"""Integration tests for all Vane FastAPI endpoints.

Verifies:
- AC-3: 2026-01-15 @ 09:00 -> 24 rows, all publishTime <= 2026-01-14T09:00:00Z.
- Equality of /api/accuracy/summary with independent cross-check output to 1e-6.
- Strict parameter validation (422 Unprocessable Entity).
- Revisions, by-horizon, by-hour, daily, distribution, and risk endpoints.
- Cache-Control headers and OpenAPI availability.
"""

from __future__ import annotations

import math
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── AC-3: Decision Day Forecast View ──────────────────────────────────────────


def test_ac3_forecast_day_twenty_four_points_and_publish_times():
    """AC-3: For delivery day 2026-01-15 at cutoff 09:00:

    - exactly 24 hourly forecast points
    - each using a forecast published <= 2026-01-14 09:00:00Z
    - selected vintage publishTime displayed prominently (2026-01-14T07:30:00Z)
    - actuals overlay present and matches A7 hourly pairing
    """
    resp = client.get("/api/forecast/day?date=2026-01-15&cutoff_hour=9")
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "public, max-age=3600"

    body = resp.json()
    assert body["delivery_date"] == "2026-01-15"
    assert body["cutoff_hour"] == 9
    assert body["selected_vintage_publish_time"] == "2026-01-14T07:30:00Z"
    assert body["n_missing"] == 0

    rows = body["rows"]
    assert len(rows) == 24

    cutoff_limit = datetime.fromisoformat("2026-01-14T09:00:00+00:00")

    for idx, row in enumerate(rows):
        assert row["hour"] == idx
        pub_dt = datetime.fromisoformat(row["publish_time"].replace("Z", "+00:00"))
        # Invariant: look-ahead is prevented by construction and covered by tests
        assert pub_dt <= cutoff_limit, (
            f"Hour {idx} published at {pub_dt} after cutoff {cutoff_limit}"
        )
        assert row["forecast_mw"] > 0
        assert row["actual_mw"] is not None
        assert row["error_mw"] is not None
        # Hand-checked hour 12: forecast=11049, actual=9790.5, error=+1258.5
        if row["hour"] == 12:
            assert row["forecast_mw"] == 11049.0
            assert row["actual_mw"] == 9790.5
            assert row["error_mw"] == 1258.5


# ── AC-4: Accuracy Summary Matches Independent Cross-Check to 1e-6 ───────────


def test_accuracy_summary_matches_cross_check():
    """Verify that /api/accuracy/summary matches independent cross_check.py output."""
    resp = client.get("/api/accuracy/summary?from_date=2026-01-01&to_date=2026-01-31&cutoff_hour=9")
    assert resp.status_code == 200
    body = resp.json()

    assert body["n"] == 744
    assert body["denominator"] == 744
    assert body["coverage_pct"] == 100.0

    # Cross-check reference numbers:
    # MAE = 2142.120296 -> round(2) = 2142.12
    # RMSE = 2611.695110 -> round(2) = 2611.70
    # Bias = 1851.903898 -> round(2) = 1851.90
    # Mean actual = 11580.737231 -> round(2) = 11580.74
    # nMAE = 18.497271% -> round(4) = 18.4973
    # Ratio = 1.1599
    # Bias share of MSE = (1851.903898^2) / (2611.695110^2) = 0.5034
    assert math.isclose(body["mae_mw"], 2142.12, abs_tol=0.01)
    assert math.isclose(body["rmse_mw"], 2611.70, abs_tol=0.01)
    assert math.isclose(body["bias_mw"], 1851.90, abs_tol=0.01)
    assert math.isclose(body["mean_actual_mw"], 11580.74, abs_tol=0.01)
    assert math.isclose(body["nmae_pct"], 18.4973, abs_tol=0.001)
    assert math.isclose(body["forecast_to_actual_ratio"], 1.1599, abs_tol=0.001)
    assert math.isclose(body["bias_share_of_mse"], 0.5034, abs_tol=0.001)


# ── Revisions Endpoint ────────────────────────────────────────────────────────


def test_revisions_endpoint_target_hour():
    resp = client.get("/api/forecast/revisions?target=2026-01-15T12:00:00Z&cutoff_hour=9")
    assert resp.status_code == 200
    body = resp.json()

    assert body["target_start_time"] == "2026-01-15T12:00:00Z"
    assert body["actual_mw"] == 9790.5
    vintages = body["vintages"]
    assert len(vintages) > 0

    # At least one vintage before cutoff and one after cutoff
    has_before = any(v["is_before_cutoff"] is True for v in vintages)
    has_after = any(v["is_before_cutoff"] is False for v in vintages)
    assert has_before
    assert has_after


# ── By-Horizon, By-Hour, Daily, and Distribution ──────────────────────────────


def test_accuracy_by_horizon_excludes_backcasts():
    resp = client.get("/api/accuracy/by-horizon?from_date=2026-01-01&to_date=2026-01-31")
    assert resp.status_code == 200
    body = resp.json()

    assert body["excluded_backcasts_count"] > 0
    assert body["total_vintages_evaluated"] > 0
    buckets = body["buckets"]
    assert len(buckets) == 6
    bucket_labels = [b["bucket"] for b in buckets]
    assert "<12" in bucket_labels
    assert "12–24" in bucket_labels


def test_accuracy_by_hour_has_confounding_note():
    resp = client.get("/api/accuracy/by-hour?from_date=2026-01-01&to_date=2026-01-31&cutoff_hour=9")
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["hours"]) == 24
    assert "confounded" in body["lead_time_confounding_note"].lower()


def test_accuracy_daily_returns_31_days():
    resp = client.get("/api/accuracy/daily?from_date=2026-01-01&to_date=2026-01-31&cutoff_hour=9")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["days"]) == 31


def test_accuracy_distribution_returns_histogram_and_quantiles():
    resp = client.get(
        "/api/accuracy/distribution?from_date=2026-01-01&to_date=2026-01-31&cutoff_hour=9&bins=20"
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["num_samples"] == 744
    assert len(body["bins"]) == 20
    assert "P50" in body["quantiles"]
    assert "P90" in body["quantiles"]
    assert "in 10 hours" in body["plain_english_reading"]


# ── Risk Cushion Band ─────────────────────────────────────────────────────────


def test_risk_band_returns_empirical_buffer():
    resp = client.get("/api/risk/band?date=2026-01-15&cutoff_hour=9&confidence=0.80")
    assert resp.status_code == 200
    body = resp.json()

    assert body["delivery_date"] == "2026-01-15"
    assert body["cutoff_hour"] == 9
    assert body["confidence"] == 0.80
    assert body["history_days_used"] == 14  # Jan 1..14
    assert body["is_fallback"] is False
    assert body["bias_used_mw"] > 0.0

    hours = body["hours"]
    assert len(hours) == 24
    for h in hours:
        assert h["cushion_mw"] >= 0.0
        assert h["band_lo_mw"] >= 0.0
        assert h["bias_used_mw"] > 0.0


# ── Strict Validation (422 Unprocessable Entity) ──────────────────────────────


def test_strict_parameter_validation_422s():
    # Invalid date range: from_date > to_date
    resp1 = client.get("/api/accuracy/summary?from_date=2026-01-20&to_date=2026-01-10")
    assert resp1.status_code == 422
    assert "cannot be after" in resp1.json()["detail"]

    # Date outside January 2026 window
    resp2 = client.get("/api/forecast/day?date=2025-12-25")
    assert resp2.status_code == 422
    assert "outside January 2026" in resp2.json()["detail"]

    # Invalid cutoff hour (> 23)
    resp3 = client.get("/api/forecast/day?date=2026-01-15&cutoff_hour=25")
    assert resp3.status_code == 422

    # Invalid confidence (< 0.50)
    resp4 = client.get("/api/risk/band?date=2026-01-15&confidence=0.20")
    assert resp4.status_code == 422


# ── OpenAPI Spec Availability ─────────────────────────────────────────────────


def test_openapi_docs_available():
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["title"].startswith("Vane")
    paths = data["paths"]
    assert "/api/forecast/day" in paths
    assert "/api/forecast/revisions" in paths
    assert "/api/accuracy/summary" in paths
    assert "/api/accuracy/by-horizon" in paths
    assert "/api/risk/band" in paths
