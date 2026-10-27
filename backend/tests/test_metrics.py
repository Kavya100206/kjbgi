"""Tests for app.domain.metrics — analytical accuracy metrics."""

from __future__ import annotations

import math

import numpy as np

from app.domain.metrics import compute_metrics_dict, compute_quantiles


def test_hand_computed_fixture():
    # Hand-crafted values:
    # errors = [+20.0, -20.0, +50.0, 0.0]
    # actuals = [80.0, 220.0, 250.0, 400.0]
    # forecasts = [100.0, 200.0, 300.0, 400.0]
    errors = [20.0, -20.0, 50.0, 0.0]
    actuals = [80.0, 220.0, 250.0, 400.0]
    forecasts = [100.0, 200.0, 300.0, 400.0]

    # Hand calculations:
    # abs_errors = [20, 20, 50, 0] -> sum = 90 -> MAE = 90 / 4 = 22.5
    # sq_errors = [400, 400, 2500, 0] -> sum = 3300 -> mean = 825 -> RMSE = sqrt(825) ≈ 28.7228
    # bias = (20 - 20 + 50 + 0) / 4 = 12.5
    # mean_actual = (80 + 220 + 250 + 400) / 4 = 237.5
    # nMAE = (22.5 / 237.5) * 100 ≈ 9.4737%
    # worst_over_forecast = 50.0
    res = compute_metrics_dict(errors, actuals, forecasts, denominator=10)

    assert res["n"] == 4
    assert res["denominator"] == 10
    assert res["coverage_pct"] == 40.0
    assert res["mae_mw"] == 22.5
    assert math.isclose(res["rmse_mw"], math.sqrt(825), rel_tol=1e-3)
    assert res["bias_mw"] == 12.5
    assert res["mean_actual_mw"] == 237.5
    assert res["mean_forecast_mw"] == 250.0
    assert math.isclose(res["error_std_mw"], math.sqrt(668.75), rel_tol=1e-3)
    assert math.isclose(res["forecast_to_actual_ratio"], 250.0 / 237.5, rel_tol=1e-3)
    assert math.isclose(res["bias_share_of_mse"], (12.5**2) / 825.0, rel_tol=1e-3)
    assert math.isclose(res["nmae_pct"], (22.5 / 237.5) * 100, rel_tol=1e-3)
    assert res["worst_over_forecast_mw"] == 50.0


def test_empty_and_nan_inputs():
    # Empty inputs
    res_empty = compute_metrics_dict([], [], denominator=744)
    assert res_empty["n"] == 0
    assert res_empty["denominator"] == 744
    assert res_empty["coverage_pct"] == 0.0
    assert res_empty["mae_mw"] is None
    assert res_empty["rmse_mw"] is None
    assert res_empty["bias_mw"] is None
    assert res_empty["nmae_pct"] is None

    # All NaNs
    res_nan = compute_metrics_dict([np.nan, np.nan], [np.nan, np.nan], denominator=744)
    assert res_nan["n"] == 0
    assert res_nan["mae_mw"] is None

    # Partially NaN: only valid pairs are evaluated
    res_partial = compute_metrics_dict(
        [10.0, np.nan, 20.0],
        [100.0, 200.0, np.nan],
        denominator=10,
    )
    # Only index 0 has both error and actual present
    assert res_partial["n"] == 1
    assert res_partial["mae_mw"] == 10.0
    assert res_partial["coverage_pct"] == 10.0


def test_zero_actual_handles_nmae_cleanly():
    # When mean actual is 0 MW, nMAE is None rather than dividing by zero
    res = compute_metrics_dict([10.0, -10.0], [0.0, 0.0])
    assert res["n"] == 2
    assert res["mae_mw"] == 10.0
    assert res["mean_actual_mw"] == 0.0
    assert res["nmae_pct"] is None


def test_compute_quantiles():
    data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    q = compute_quantiles(data, quantiles=(0.1, 0.5, 0.9))
    assert q["P10"] == 19.0
    assert q["P50"] == 55.0
    assert q["P90"] == 91.0

    # Empty data
    empty_q = compute_quantiles([])
    assert math.isnan(empty_q["P50"])
