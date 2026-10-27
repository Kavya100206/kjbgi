"""Assumption A7: Hourly actual pairing.

GB wind actuals (FUELHH) are reported every 30 minutes (:00 and :30).
Wind forecasts (WINDFOR) are published at hourly resolution (:00 only).

Pairing Rule (A7):
    actual_hourly(H) = mean(FUELHH[H:00], FUELHH[H:30])

If either half-hour is missing, that hour is excluded and counted in coverage (no fill).
Scoring denominator = 24 target hours * 31 days = 744 hours for January 2026.
"""

from __future__ import annotations

import pandas as pd


def compute_hourly_actuals(
    actuals_df: pd.DataFrame,
    start_time_col: str = "startTime",
    generation_col: str = "generation",
) -> pd.DataFrame:
    """Aggregate 30-minute FUELHH actuals into hourly means per Assumption A7.

    For each target hour H:00:00Z, finds H:00:00Z and H:30:00Z.
    An hour is complete ONLY if BOTH half-hours are present.
    If either half is missing, is_complete=False and actual_mw is NaN (excluded).

    Args:
        actuals_df: DataFrame with 30-minute FUELHH actuals.
        start_time_col: Name of column containing UTC datetimes.
        generation_col: Name of column containing generation in MW.

    Returns:
        DataFrame with columns:
            startTime: Hourly UTC datetime (at :00:00)
            actual_mw: Hourly mean MW (or NaN if incomplete)
            is_complete: Boolean indicating whether both half-hours were present
            h00_mw: Generation at H:00
            h30_mw: Generation at H:30
    """
    if actuals_df.empty:
        return pd.DataFrame(columns=["startTime", "actual_mw", "is_complete", "h00_mw", "h30_mw"])

    df = actuals_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[start_time_col]):
        df[start_time_col] = pd.to_datetime(df[start_time_col], utc=True)

    # Floor to the beginning of the hour (e.g. 14:00 and 14:30 both map to 14:00)
    df["hour_start"] = df[start_time_col].dt.floor("1h")
    df["minute"] = df[start_time_col].dt.minute

    # Pivot to get :00 and :30 side-by-side
    pivoted = df.pivot_table(
        index="hour_start",
        columns="minute",
        values=generation_col,
        aggfunc="first",
    ).reset_index()

    pivoted = pivoted.rename(columns={"hour_start": "startTime"})

    # Ensure columns 0 and 30 exist even if a chunk had none
    if 0 not in pivoted.columns:
        pivoted[0] = float("nan")
    if 30 not in pivoted.columns:
        pivoted[30] = float("nan")

    pivoted = pivoted.rename(columns={0: "h00_mw", 30: "h30_mw"})

    # A7 Rule: Both halves must be present
    both_present = pivoted["h00_mw"].notna() & pivoted["h30_mw"].notna()
    pivoted["is_complete"] = both_present.astype(bool)
    pivoted["actual_mw"] = float("nan")
    pivoted.loc[both_present, "actual_mw"] = (
        pivoted.loc[both_present, "h00_mw"] + pivoted.loc[both_present, "h30_mw"]
    ) / 2.0

    result = pivoted[["startTime", "actual_mw", "is_complete", "h00_mw", "h30_mw"]].copy()
    return result.sort_values("startTime").reset_index(drop=True)


def pair_forecast_and_actual(
    forecasts_df: pd.DataFrame,
    actuals_df: pd.DataFrame,
    forecast_col: str = "generation",
) -> pd.DataFrame:
    """Pair hourly forecasts with hourly mean actuals (A7).

    Args:
        forecasts_df: DataFrame with hourly forecasts (must contain startTime).
        actuals_df: DataFrame with 30-min FUELHH actuals.
        forecast_col: Name of generation column in forecasts_df.

    Returns:
        DataFrame with columns:
            startTime: Hourly UTC datetime
            forecast_mw: Forecast value in MW
            actual_mw: Hourly mean actual in MW (or NaN if incomplete)
            error_mw: forecast_mw - actual_mw (positive = over-forecast)
            is_paired: True if both forecast and complete actual exist
            is_actual_complete: True if both actual halves were present
    """
    if forecasts_df.empty:
        return pd.DataFrame(
            columns=[
                "startTime",
                "forecast_mw",
                "actual_mw",
                "error_mw",
                "is_paired",
                "is_actual_complete",
            ]
        )

    fc = forecasts_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(fc["startTime"]):
        fc["startTime"] = pd.to_datetime(fc["startTime"], utc=True)

    hourly_act = compute_hourly_actuals(actuals_df)

    merged = pd.merge(
        fc,
        hourly_act,
        on="startTime",
        how="left",
    )

    merged = merged.rename(columns={forecast_col: "forecast_mw"})
    if "is_complete" in merged.columns:
        merged = merged.rename(columns={"is_complete": "is_actual_complete"})
        merged["is_actual_complete"] = merged["is_actual_complete"].fillna(False).astype(bool)
    else:
        merged["is_actual_complete"] = False

    merged["is_paired"] = (
        merged["is_actual_complete"] & merged["actual_mw"].notna() & merged["forecast_mw"].notna()
    ).astype(bool)

    merged["error_mw"] = float("nan")
    paired_mask = merged["is_paired"]
    # A3 Sign convention: error = forecast - actual (positive = over-forecast)
    merged.loc[paired_mask, "error_mw"] = (
        merged.loc[paired_mask, "forecast_mw"] - merged.loc[paired_mask, "actual_mw"]
    )

    return merged
