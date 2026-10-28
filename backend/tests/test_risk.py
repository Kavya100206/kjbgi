"""Tests for app.domain.risk — empirical risk bands and cushion calculation."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from app.domain.risk import compute_risk_band


def test_proves_no_use_of_same_day_or_later_errors():
    """CRITICAL TEST: Proves that same-day or future errors NEVER affect the risk band."""
    delivery_date = date(2026, 1, 10)

    # Historical data for Days 1 through 15
    dates = pd.date_range("2026-01-01 00:00:00+00:00", "2026-01-15 23:00:00+00:00", freq="1h")
    # Constant baseline error of +100 MW
    base_df = pd.DataFrame(
        {
            "startTime": dates,
            "forecast_mw": 8000.0,
            "actual_mw": 7900.0,
            "error_mw": 100.0,
            "is_paired": True,
        }
    )

    day_fc = base_df[base_df["startTime"].dt.date == delivery_date][["startTime", "forecast_mw"]]

    res_clean = compute_risk_band(
        delivery_date=delivery_date,
        cutoff_hour=9,
        paired_history_df=base_df,
        day_forecasts_df=day_fc,
        confidence=0.80,
    )

    # Now create poisoned DataFrame with massive extreme errors on Day 10 (same-day) and Day 11 (future)
    poisoned_df = base_df.copy()
    same_day_mask = poisoned_df["startTime"].dt.date == delivery_date
    future_mask = poisoned_df["startTime"].dt.date > delivery_date

    poisoned_df.loc[same_day_mask, "error_mw"] = 999999.0
    poisoned_df.loc[future_mask, "error_mw"] = 888888.0

    res_poisoned = compute_risk_band(
        delivery_date=delivery_date,
        cutoff_hour=9,
        paired_history_df=poisoned_df,
        day_forecasts_df=day_fc,
        confidence=0.80,
    )

    # Verify results are identical
    assert res_clean["history_days_used"] == res_poisoned["history_days_used"] == 9  # Days 1..9
    assert res_clean["is_fallback"] == res_poisoned["is_fallback"] is False
    assert res_clean["bias_used_mw"] == res_poisoned["bias_used_mw"] == 100.0

    for clean_h, poisoned_h in zip(res_clean["hours"], res_poisoned["hours"], strict=True):
        assert clean_h["band_lo_mw"] == poisoned_h["band_lo_mw"]
        assert clean_h["band_hi_mw"] == poisoned_h["band_hi_mw"]
        assert clean_h["cushion_mw"] == poisoned_h["cushion_mw"]
        assert clean_h["bias_used_mw"] == poisoned_h["bias_used_mw"] == 100.0


def test_fallback_flag_when_history_under_3_days():
    # Only 2 days of history before Jan 3
    dates = pd.date_range("2026-01-01 00:00:00+00:00", "2026-01-02 23:00:00+00:00", freq="1h")
    hist_df = pd.DataFrame(
        {
            "startTime": dates,
            "forecast_mw": 5000.0,
            "actual_mw": 4800.0,
            "error_mw": 200.0,
            "is_paired": True,
        }
    )

    day_fc = pd.DataFrame([{"startTime": "2026-01-03T12:00:00Z", "forecast_mw": 6000.0}])

    # For delivery Jan 3: prior days = 2 (Jan 1, Jan 2) -> is_fallback is True
    res = compute_risk_band(
        delivery_date=date(2026, 1, 3),
        cutoff_hour=9,
        paired_history_df=hist_df,
        day_forecasts_df=day_fc,
        min_history_days=3,
    )
    assert res["history_days_used"] == 2
    assert res["is_fallback"] is True


def test_confidence_level_widens_band():
    dates = pd.date_range("2026-01-01 00:00:00+00:00", "2026-01-05 23:00:00+00:00", freq="1h")
    np.random.seed(42)
    errors = np.random.normal(loc=50.0, scale=300.0, size=len(dates))
    hist_df = pd.DataFrame(
        {
            "startTime": dates,
            "forecast_mw": 7000.0,
            "actual_mw": 7000.0 - errors,
            "error_mw": errors,
            "is_paired": True,
        }
    )
    day_fc = pd.DataFrame([{"startTime": "2026-01-06T12:00:00Z", "forecast_mw": 7000.0}])

    res_80 = compute_risk_band(
        delivery_date=date(2026, 1, 6),
        cutoff_hour=9,
        paired_history_df=hist_df,
        day_forecasts_df=day_fc,
        confidence=0.80,
    )
    res_95 = compute_risk_band(
        delivery_date=date(2026, 1, 6),
        cutoff_hour=9,
        paired_history_df=hist_df,
        day_forecasts_df=day_fc,
        confidence=0.95,
    )

    width_80 = res_80["hours"][0]["band_hi_mw"] - res_80["hours"][0]["band_lo_mw"]
    width_95 = res_95["hours"][0]["band_hi_mw"] - res_95["hours"][0]["band_lo_mw"]
    assert width_95 > width_80


def test_band_lo_clipped_at_zero():
    dates = pd.date_range("2026-01-01 00:00:00+00:00", "2026-01-05 23:00:00+00:00", freq="1h")
    # Enormous positive error (+5000 MW)
    hist_df = pd.DataFrame(
        {
            "startTime": dates,
            "forecast_mw": 6000.0,
            "actual_mw": 1000.0,
            "error_mw": 5000.0,
            "is_paired": True,
        }
    )
    # Small forecast 500 MW - 5000 MW error would be negative without clipping
    day_fc = pd.DataFrame([{"startTime": "2026-01-06T12:00:00Z", "forecast_mw": 500.0}])

    res = compute_risk_band(
        delivery_date=date(2026, 1, 6),
        cutoff_hour=9,
        paired_history_df=hist_df,
        day_forecasts_df=day_fc,
        confidence=0.80,
    )
    assert res["hours"][0]["band_lo_mw"] == 0.0
