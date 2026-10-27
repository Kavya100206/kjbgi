"""Pure analytical metrics module for wind forecast accuracy evaluation.

Implements standard energy trading error metrics:
    error = forecast - actual (positive = over-forecast = buyer shortfall risk)
    MAE = mean(|error|)
    RMSE = sqrt(mean(error^2))
    Bias = mean(error)
    nMAE = MAE / mean(actual) (reported as %)
    Pxx abs error = linear percentile of |error|
    Over-forecast tail: P90 of max(error, 0), worst over-forecast = max(error)
    Coverage = n / denominator (denominator = 744 for full January)

Pure functions only — no file I/O or network calls.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd


def compute_metrics_dict(
    errors: Sequence[float] | np.ndarray | pd.Series,
    actuals: Sequence[float] | np.ndarray | pd.Series,
    forecasts: Sequence[float] | np.ndarray | pd.Series | None = None,
    denominator: int | None = None,
) -> dict[str, Any]:
    """Compute headline accuracy metrics from paired error and actual vectors.

    Args:
        errors: Sequence of (forecast - actual) values in MW.
        actuals: Sequence of paired hourly mean actuals in MW.
        forecasts: Optional sequence of paired forecasts in MW.
        denominator: Expected total periods for coverage calculation (e.g. 744 for Jan).

    Returns:
        Dictionary with all computed metrics (None for metrics when n == 0).
    """
    err_arr = np.asarray(errors, dtype=float)
    act_arr = np.asarray(actuals, dtype=float)

    # Filter out NaNs to ensure strict pairing
    valid_mask = ~np.isnan(err_arr) & ~np.isnan(act_arr)
    err_clean = err_arr[valid_mask]
    act_clean = act_arr[valid_mask]

    n = len(err_clean)
    total_expected = denominator if denominator is not None and denominator > 0 else n
    coverage_pct = round((n / total_expected) * 100.0, 2) if total_expected > 0 else 0.0

    if n == 0:
        return {
            "n": 0,
            "denominator": total_expected,
            "coverage_pct": coverage_pct,
            "mae_mw": None,
            "rmse_mw": None,
            "bias_mw": None,
            "nmae_pct": None,
            "mean_actual_mw": None,
            "mean_forecast_mw": None,
            "p50_abs_error_mw": None,
            "p90_abs_error_mw": None,
            "p95_abs_error_mw": None,
            "p90_over_forecast_mw": None,
            "worst_over_forecast_mw": None,
        }

    abs_errors = np.abs(err_clean)
    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(err_clean**2)))
    bias = float(np.mean(err_clean))
    mean_act = float(np.mean(act_clean))

    # Normalized MAE: MAE / mean_actual (%)
    nmae_pct = round((mae / mean_act) * 100.0, 4) if mean_act > 0 else None

    # Quantiles using standard linear interpolation
    p50_abs = float(np.percentile(abs_errors, 50))
    p90_abs = float(np.percentile(abs_errors, 90))
    p95_abs = float(np.percentile(abs_errors, 95))

    # Over-forecast metrics: positive errors only
    over_errors = np.maximum(err_clean, 0.0)
    p90_over = float(np.percentile(over_errors, 90))
    worst_over = float(np.max(err_clean))

    mean_fc: float | None = None
    if forecasts is not None:
        fc_arr = np.asarray(forecasts, dtype=float)[valid_mask]
        mean_fc = round(float(np.mean(fc_arr)), 2)

    return {
        "n": n,
        "denominator": total_expected,
        "coverage_pct": coverage_pct,
        "mae_mw": round(mae, 2),
        "rmse_mw": round(rmse, 2),
        "bias_mw": round(bias, 2),
        "nmae_pct": nmae_pct,
        "mean_actual_mw": round(mean_act, 2),
        "mean_forecast_mw": mean_fc,
        "p50_abs_error_mw": round(p50_abs, 2),
        "p90_abs_error_mw": round(p90_abs, 2),
        "p95_abs_error_mw": round(p95_abs, 2),
        "p90_over_forecast_mw": round(p90_over, 2),
        "worst_over_forecast_mw": round(worst_over, 2),
    }


def compute_quantiles(
    values: Sequence[float] | np.ndarray | pd.Series,
    quantiles: Sequence[float] = (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95),
) -> dict[str, float]:
    """Compute empirical quantiles for a series of values."""
    arr = np.asarray(values, dtype=float)
    clean = arr[~np.isnan(arr)]
    if len(clean) == 0:
        return {f"P{int(q * 100)}": float("nan") for q in quantiles}

    res = {}
    for q in quantiles:
        key = f"P{int(round(q * 100))}"
        res[key] = round(float(np.percentile(clean, q * 100)), 2)
    return res
