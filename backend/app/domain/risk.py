"""Risk buffer and empirical error band calculation (FR-7).

For a delivery day D, calculates an empirical error band [band_lo, band_hi] and
the implied MW cushion.

Core Invariant:
    Look-ahead is prevented by construction and covered by tests. Only historical delivery days strictly BEFORE D (prior_date < D)
    at the same cutoff are used. If fewer than 3 prior days of history exist,
    fallback_flag is True.

Sign Convention & Formulas:
    error = forecast - actual  (positive = over-forecast = risk of buying too little)
    actual = forecast - error

For chosen confidence (e.g. 80% -> P10 to P90 of prior errors [q_lo, q_hi]):
    band_lo = max(0, forecast - q_hi)
    band_hi = max(0, forecast - q_lo)
    cushion_mw = max(0, q_hi) (implied reserve buffer against over-forecast shortfall)
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd


def compute_risk_band(
    delivery_date: date,
    cutoff_hour: int,
    paired_history_df: pd.DataFrame,
    day_forecasts_df: pd.DataFrame,
    confidence: float = 0.80,
    min_history_days: int = 3,
) -> dict[str, Any]:
    """Compute empirical error bands and MW cushion for delivery day D.

    Args:
        delivery_date: Target delivery day D.
        cutoff_hour: Cutoff hour on D-1 (0..23).
        paired_history_df: All available paired historical records (must have startTime, error_mw, is_paired).
        day_forecasts_df: Decision-time forecasts for day D (must have startTime, forecast_mw).
        confidence: Confidence level for the empirical interval (e.g. 0.80 for 80% band).
        min_history_days: Minimum prior days required to avoid fallback flag (default 3).

    Returns:
        Dictionary with metadata and hourly bands:
            delivery_date: ISO date string
            cutoff_hour: Cutoff hour used
            confidence: Confidence level
            history_days_used: Count of distinct prior delivery days used
            is_fallback: True if history_days_used < min_history_days
            hours: List of per-period forecast, band_lo_mw, band_hi_mw, cushion_mw
    """
    if not (0.50 <= confidence < 1.0):
        raise ValueError(f"Confidence must be between 0.50 and 1.0, got {confidence}")

    alpha = (1.0 - confidence) / 2.0
    q_lo_pct = alpha * 100.0
    q_hi_pct = (1.0 - alpha) * 100.0

    # Ensure UTC datetimes
    hist = paired_history_df.copy()
    if not hist.empty and not pd.api.types.is_datetime64_any_dtype(hist["startTime"]):
        hist["startTime"] = pd.to_datetime(hist["startTime"], utc=True)

    day_fc = day_forecasts_df.copy()
    if not day_fc.empty and not pd.api.types.is_datetime64_any_dtype(day_fc["startTime"]):
        day_fc["startTime"] = pd.to_datetime(day_fc["startTime"], utc=True)

    # STRICT INVARIANT: Prior days only (delivery date strictly < D)
    if not hist.empty and "is_paired" in hist.columns:
        prior_mask = (hist["startTime"].dt.date < delivery_date) & hist["is_paired"]
        prior_df = hist[prior_mask].copy()
    else:
        prior_df = pd.DataFrame()

    history_days_used = int(prior_df["startTime"].dt.date.nunique()) if not prior_df.empty else 0
    is_fallback = history_days_used < min_history_days

    # Extract prior error distribution
    prior_errors: np.ndarray = (
        prior_df["error_mw"].dropna().values if not prior_df.empty else np.array([], dtype=float)
    )

    hours_result: list[dict[str, Any]] = []

    # Sort day forecasts chronologically
    if not day_fc.empty:
        day_fc = day_fc.sort_values("startTime").reset_index(drop=True)

    for _, row in day_fc.iterrows():
        t = row["startTime"]
        fc_val = float(row["forecast_mw"]) if pd.notna(row.get("forecast_mw")) else 0.0

        if len(prior_errors) > 0:
            # Hour-of-day matching if sufficient samples exist (>= 7 prior days), else pool all prior hours
            h = t.hour
            hour_subset = prior_df[prior_df["startTime"].dt.hour == h]["error_mw"].dropna().values
            err_sample = hour_subset if len(hour_subset) >= 7 else prior_errors

            q_lo = float(np.percentile(err_sample, q_lo_pct))
            q_hi = float(np.percentile(err_sample, q_hi_pct))
            bias_val = round(float(np.mean(err_sample)), 1)

            # actual = forecast - error
            band_lo = max(0.0, round(fc_val - q_hi, 1))
            band_hi = max(0.0, round(fc_val - q_lo, 1))
            cushion = max(0.0, round(q_hi, 1))
        else:
            # Zero prior history fallback
            band_lo = round(fc_val, 1)
            band_hi = round(fc_val, 1)
            cushion = 0.0
            bias_val = 0.0

        hours_result.append(
            {
                "startTime": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "hour": t.hour,
                "forecast_mw": round(fc_val, 1),
                "band_lo_mw": band_lo,
                "band_hi_mw": band_hi,
                "cushion_mw": cushion,
                "bias_used_mw": bias_val,
            }
        )

    overall_bias = round(float(np.mean(prior_errors)), 1) if len(prior_errors) > 0 else 0.0

    return {
        "delivery_date": delivery_date.isoformat(),
        "cutoff_hour": cutoff_hour,
        "confidence": confidence,
        "history_days_used": history_days_used,
        "is_fallback": is_fallback,
        "bias_used_mw": overall_bias,
        "hours": hours_result,
    }
