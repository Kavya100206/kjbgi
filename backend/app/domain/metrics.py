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
            "error_std_mw": None,
            "nmae_pct": None,
            "mean_actual_mw": None,
            "mean_forecast_mw": None,
            "forecast_to_actual_ratio": None,
            "bias_share_of_mse": None,
            "p50_abs_error_mw": None,
            "p90_abs_error_mw": None,
            "p95_abs_error_mw": None,
            "p90_over_forecast_mw": None,
            "worst_over_forecast_mw": None,
        }

    abs_errors = np.abs(err_clean)
    mae = float(np.mean(abs_errors))
    mse = float(np.mean(err_clean**2))
    rmse = float(np.sqrt(mse))
    bias = float(np.mean(err_clean))
    error_std = float(np.std(err_clean, ddof=0))
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

    if forecasts is not None:
        fc_arr = np.asarray(forecasts, dtype=float)[valid_mask]
        mean_fc = float(np.mean(fc_arr))
    else:
        # Since error = forecast - actual, forecast = actual + error
        mean_fc = float(np.mean(act_clean + err_clean))

    ratio_fc_act = round(mean_fc / mean_act, 4) if mean_act > 0 else None
    bias_share_mse = round((bias**2) / mse, 4) if mse > 0 else None

    return {
        "n": n,
        "denominator": total_expected,
        "coverage_pct": coverage_pct,
        "mae_mw": round(mae, 2),
        "rmse_mw": round(rmse, 2),
        "bias_mw": round(bias, 2),
        "error_std_mw": round(error_std, 2),
        "nmae_pct": nmae_pct,
        "mean_actual_mw": round(mean_act, 2),
        "mean_forecast_mw": round(mean_fc, 2),
        "forecast_to_actual_ratio": ratio_fc_act,
        "bias_share_of_mse": bias_share_mse,
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


# ── Aggregations ──────────────────────────────────────────────────────────────


def aggregate_by_hour(paired_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Group paired decision-time forecasts by hour of day (0..23).

    Note: The UI must disclose that lead time is confounded with hour-of-day
    (~16.5 h for 00:00 to ~39.5 h for 23:00 from a 09:00 morning cutoff).
    """
    if paired_df.empty:
        return []

    df = paired_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["startTime"]):
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)

    df["hour"] = df["startTime"].dt.hour
    num_days = df["startTime"].dt.date.nunique()

    rows: list[dict[str, Any]] = []
    for hour in range(24):
        hour_df = df[df["hour"] == hour]
        metrics = compute_metrics_dict(
            hour_df["error_mw"],
            hour_df["actual_mw"],
            hour_df.get("forecast_mw"),
            denominator=num_days,
        )
        rows.append(
            {
                "hour": hour,
                "n": metrics["n"],
                "denominator": metrics["denominator"],
                "mae_mw": metrics["mae_mw"],
                "rmse_mw": metrics["rmse_mw"],
                "bias_mw": metrics["bias_mw"],
                "nmae_pct": metrics["nmae_pct"],
                "mean_actual_mw": metrics["mean_actual_mw"],
                "mean_forecast_mw": metrics["mean_forecast_mw"],
            }
        )
    return rows


def aggregate_daily(paired_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Group paired decision-time forecasts by delivery day."""
    if paired_df.empty:
        return []

    df = paired_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["startTime"]):
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)

    df["date"] = df["startTime"].dt.date
    unique_dates = sorted(df["date"].unique())

    rows: list[dict[str, Any]] = []
    for d in unique_dates:
        day_df = df[df["date"] == d]
        metrics = compute_metrics_dict(
            day_df["error_mw"],
            day_df["actual_mw"],
            day_df.get("forecast_mw"),
            denominator=24,  # 24 hours per day
        )
        rows.append(
            {
                "date": d.isoformat(),
                "n": metrics["n"],
                "denominator": 24,
                "coverage_pct": metrics["coverage_pct"],
                "mae_mw": metrics["mae_mw"],
                "rmse_mw": metrics["rmse_mw"],
                "bias_mw": metrics["bias_mw"],
                "nmae_pct": metrics["nmae_pct"],
                "mean_actual_mw": metrics["mean_actual_mw"],
                "mean_forecast_mw": metrics["mean_forecast_mw"],
            }
        )
    return rows


HORIZON_BUCKETS: list[tuple[str, float, float]] = [
    ("<12", 0.0, 12.0),
    ("12–24", 12.0, 24.0),
    ("24–36", 24.0, 36.0),
    ("36–48", 36.0, 48.0),
    ("48–60", 48.0, 60.0),
    ("60–67", 60.0, 67.5),
]


def aggregate_by_horizon(
    all_forecasts_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
) -> dict[str, Any]:
    """Evaluate accuracy across ALL vintages bucketed by forecast horizon.

    Filters out retrospective backcasts (horizon < 0) and reports their count.
    Buckets forward forecasts: <12, 12-24, 24-36, 36-48, 48-60, 60-67 hours.
    """
    from app.domain.pairing import pair_forecast_and_actual

    if all_forecasts_df.empty or actuals_df.empty:
        return {
            "buckets": [],
            "excluded_backcasts_count": 0,
            "total_evaluated_count": 0,
        }

    # Pair all forecast vintages with hourly actuals
    paired = pair_forecast_and_actual(all_forecasts_df, actuals_df)
    valid_paired = paired[paired["is_paired"]].copy()

    if "horizon_h" not in valid_paired.columns:
        valid_paired["horizon_h"] = (
            valid_paired["startTime"] - pd.to_datetime(valid_paired["publishTime"], utc=True)
        ).dt.total_seconds() / 3600.0

    # Filter out retrospective backcasts (horizon < 0)
    backcasts_mask = valid_paired["horizon_h"] < 0
    excluded_backcasts_count = int(backcasts_mask.sum())
    forward_df = valid_paired[~backcasts_mask].copy()

    bucket_results: list[dict[str, Any]] = []
    for label, low, high in HORIZON_BUCKETS:
        # Semi-open interval [low, high), except last bucket includes high
        if high >= 67.0:
            mask = (forward_df["horizon_h"] >= low) & (forward_df["horizon_h"] <= high)
        else:
            mask = (forward_df["horizon_h"] >= low) & (forward_df["horizon_h"] < high)

        b_df = forward_df[mask]
        m = compute_metrics_dict(b_df["error_mw"], b_df["actual_mw"], b_df.get("forecast_mw"))
        bucket_results.append(
            {
                "bucket": label,
                "n": m["n"],
                "mae_mw": m["mae_mw"],
                "rmse_mw": m["rmse_mw"],
                "bias_mw": m["bias_mw"],
                "nmae_pct": m["nmae_pct"],
                "mean_actual_mw": m["mean_actual_mw"],
                "mean_forecast_mw": m["mean_forecast_mw"],
            }
        )

    return {
        "buckets": bucket_results,
        "excluded_backcasts_count": excluded_backcasts_count,
        "total_evaluated_count": len(forward_df),
    }


def aggregate_distribution(
    paired_df: pd.DataFrame,
    num_bins: int = 20,
) -> dict[str, Any]:
    """Compute error distribution histogram, quantiles, and plain-English reading."""
    if paired_df.empty:
        return {
            "bins": [],
            "quantiles": {},
            "total_count": 0,
            "plain_english_p90": None,
        }

    valid_errors = paired_df.loc[paired_df["is_paired"], "error_mw"].dropna().values
    if len(valid_errors) == 0:
        return {
            "bins": [],
            "quantiles": {},
            "total_count": 0,
            "plain_english_p90": None,
        }

    counts, bin_edges = np.histogram(valid_errors, bins=num_bins)
    total_count = len(valid_errors)

    bins: list[dict[str, Any]] = []
    for i in range(len(counts)):
        b_start = round(float(bin_edges[i]), 1)
        b_end = round(float(bin_edges[i + 1]), 1)
        b_mid = round((b_start + b_end) / 2.0, 1)
        c = int(counts[i])
        pct = round((c / total_count) * 100.0, 2)
        bins.append(
            {
                "bin_start": b_start,
                "bin_end": b_end,
                "bin_mid": b_mid,
                "count": c,
                "pct_of_total": pct,
            }
        )

    quantiles = compute_quantiles(valid_errors, quantiles=(0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95))

    p90_err = quantiles.get("P90", 0.0)
    plain_english = (
        f"On 1 in 10 hours (P90), the forecast was too high by ≥ {abs(p90_err):.0f} MW"
        if p90_err >= 0
        else f"On 9 in 10 hours, the forecast was within {abs(p90_err):.0f} MW"
    )

    return {
        "bins": bins,
        "quantiles": quantiles,
        "total_count": total_count,
        "plain_english_p90": plain_english,
    }
