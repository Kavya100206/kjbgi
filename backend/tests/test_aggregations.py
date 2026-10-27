"""Tests for aggregations (by-horizon, by-hour, daily, distribution) in domain.metrics.

Verifies that group totals reconcile strictly with the headline summary.
"""

from __future__ import annotations

from app.data.loader import load_actuals, load_forecasts
from app.domain.metrics import (
    aggregate_by_horizon,
    aggregate_by_hour,
    aggregate_daily,
    aggregate_distribution,
    compute_metrics_dict,
)
from app.domain.pairing import pair_forecast_and_actual
from app.domain.vintage import select_forecasts_at_cutoff


def test_aggregations_reconcile_with_summary():
    actuals = load_actuals()
    forecasts = load_forecasts()

    # January 2026 at default cutoff 09:00 UTC
    decision_fc = select_forecasts_at_cutoff(
        forecasts,
        cutoff_hour=9,
        start_date=actuals["startTime"].dt.date.min(),
        end_date=actuals["startTime"].dt.date.max(),
    )
    # Filter to January 1 to 31
    jan_mask = (decision_fc["startTime"].dt.month == 1) & (decision_fc["startTime"].dt.year == 2026)
    decision_fc_jan = decision_fc[jan_mask].copy()

    paired = pair_forecast_and_actual(decision_fc_jan, actuals)
    assert len(paired) == 744

    # 1. Headline summary
    summary = compute_metrics_dict(
        paired["error_mw"],
        paired["actual_mw"],
        paired["forecast_mw"],
        denominator=744,
    )
    assert summary["n"] == 744
    assert summary["coverage_pct"] == 100.0
    assert summary["mae_mw"] is not None

    # 2. Reconcile by-hour
    by_hour = aggregate_by_hour(paired)
    assert len(by_hour) == 24
    by_hour_total_n = sum(row["n"] for row in by_hour)
    assert by_hour_total_n == summary["n"]
    for row in by_hour:
        assert 0 <= row["hour"] <= 23
        assert row["n"] == 31  # 31 days in Jan

    # 3. Reconcile daily
    daily = aggregate_daily(paired)
    assert len(daily) == 31
    daily_total_n = sum(row["n"] for row in daily)
    assert daily_total_n == summary["n"]
    for row in daily:
        assert row["n"] == 24  # 24 hours per day
        assert row["coverage_pct"] == 100.0

    # 4. Reconcile distribution
    dist = aggregate_distribution(paired, num_bins=20)
    assert len(dist["bins"]) == 20
    assert dist["total_count"] == summary["n"]
    dist_total_count = sum(b["count"] for b in dist["bins"])
    assert dist_total_count == summary["n"]
    assert "plain_english_p90" in dist
    assert "P50" in dist["quantiles"]


def test_aggregate_by_horizon_excludes_backcasts():
    actuals = load_actuals()
    forecasts = load_forecasts()

    # Filter actuals to Jan 1 to Jan 31
    jan_act = actuals[(actuals["startTime"].dt.month == 1) & (actuals["startTime"].dt.year == 2026)]

    horizon_res = aggregate_by_horizon(forecasts, jan_act)
    buckets = horizon_res["buckets"]
    assert len(buckets) == 6
    expected_labels = ["<12", "12–24", "24–36", "36–48", "48–60", "60–67"]
    assert [b["bucket"] for b in buckets] == expected_labels

    # Backcasts must be excluded and counted
    assert horizon_res["excluded_backcasts_count"] > 0
    total_in_buckets = sum(b["n"] for b in buckets)
    assert total_in_buckets == horizon_res["total_evaluated_count"]

    # Each bucket should have positive counts and sensible MAE
    for b in buckets:
        assert b["n"] > 0
        assert b["mae_mw"] > 0.0
