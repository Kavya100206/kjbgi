"""Vintage selection logic — Assumption A2.

Selects the forecast available at the decision time for each target delivery hour.

For each target hour t on delivery date D (UTC date of startTime):
    cutoff(t) = (D - 1 day) at cutoff_hour:00:00 UTC
    selected_vintage = row with max(publishTime) <= cutoff(t) for that startTime

Look-ahead is prevented by construction and covered by tests. Uses real observed publishTime timestamps only,
never hardcoded schedules.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pandas as pd


def get_cutoff_for_target(target_dt: datetime, cutoff_hour: int) -> datetime:
    """Calculate the decision cutoff timestamp for a given target delivery hour.

    Decision occurs on D-1 at cutoff_hour:00:00 UTC, where D is the UTC date of target_dt.
    """
    if not isinstance(target_dt, datetime):
        raise TypeError(f"target_dt must be datetime, got {type(target_dt)}")
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=UTC)

    d = target_dt.date() - timedelta(days=1)
    return datetime(d.year, d.month, d.day, cutoff_hour, 0, 0, tzinfo=UTC)


def select_forecasts_at_cutoff(
    forecasts_df: pd.DataFrame,
    cutoff_hour: int = 9,
    delivery_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    generation_col: str = "generation",
) -> pd.DataFrame:
    """Select the decision-time forecast for each target hour.

    Args:
        forecasts_df: DataFrame with all WINDFOR vintages (startTime, publishTime, generation).
        cutoff_hour: Hour of day on D-1 when decision is made (0..23 UTC).
        delivery_date: Optional single delivery date to filter targets.
        start_date: Optional start delivery date (inclusive).
        end_date: Optional end delivery date (inclusive).
        generation_col: Name of generation column.

    Returns:
        DataFrame with one row per target hour with an eligible vintage:
            startTime: Target hour UTC datetime
            forecast_mw: Forecast generation value in MW
            publishTime: Real publishTime of the selected vintage
            cutoff_time: Cutoff timestamp used for selection
            forecast_age_h: Hours between publishTime and cutoff (cutoff - publishTime)
            horizon_h: Lead time in hours (startTime - publishTime)
            delivery_date: UTC date of delivery
    """
    if forecasts_df.empty:
        return pd.DataFrame(
            columns=[
                "startTime",
                "forecast_mw",
                "publishTime",
                "cutoff_time",
                "forecast_age_h",
                "horizon_h",
                "delivery_date",
            ]
        )

    if not (0 <= cutoff_hour <= 23):
        raise ValueError(f"cutoff_hour must be between 0 and 23, got {cutoff_hour}")

    df = forecasts_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["startTime"]):
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    if not pd.api.types.is_datetime64_any_dtype(df["publishTime"]):
        df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)

    # Filter target delivery dates if requested
    target_dates = df["startTime"].dt.date
    if delivery_date is not None:
        df = df[target_dates == delivery_date].copy()
    else:
        if start_date is not None:
            df = df[target_dates >= start_date].copy()
        if end_date is not None:
            # Recompute target_dates after start_date filter
            df = df[df["startTime"].dt.date <= end_date].copy()

    if df.empty:
        return pd.DataFrame(
            columns=[
                "startTime",
                "forecast_mw",
                "publishTime",
                "cutoff_time",
                "forecast_age_h",
                "horizon_h",
                "delivery_date",
            ]
        )

    # Calculate cutoff for each row based on its target startTime
    # cutoff = (startTime.date - 1 day) + cutoff_hour:00:00 UTC
    target_day = df["startTime"].dt.floor("1D")
    df["cutoff_time"] = target_day - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)

    # Invariant: publishTime <= cutoff_time (look-ahead prevented by construction)
    eligible = df[df["publishTime"] <= df["cutoff_time"]].copy()
    if eligible.empty:
        return pd.DataFrame(
            columns=[
                "startTime",
                "forecast_mw",
                "publishTime",
                "cutoff_time",
                "forecast_age_h",
                "horizon_h",
                "delivery_date",
            ]
        )

    # Choose the latest vintage per target startTime: max(publishTime)
    eligible = eligible.sort_values(["startTime", "publishTime"])
    latest = eligible.groupby("startTime", as_index=False).last()

    # Rename and compute derived metrics
    latest = latest.rename(columns={generation_col: "forecast_mw"})
    latest["forecast_age_h"] = (
        (latest["cutoff_time"] - latest["publishTime"]).dt.total_seconds() / 3600.0
    ).round(4)
    latest["horizon_h"] = (
        (latest["startTime"] - latest["publishTime"]).dt.total_seconds() / 3600.0
    ).round(4)
    latest["delivery_date"] = latest["startTime"].dt.date

    cols = [
        "startTime",
        "forecast_mw",
        "publishTime",
        "cutoff_time",
        "forecast_age_h",
        "horizon_h",
        "delivery_date",
    ]
    return latest[cols].sort_values("startTime").reset_index(drop=True)


def get_vintage_revisions_for_target(
    forecasts_df: pd.DataFrame,
    target_time: datetime,
    generation_col: str = "generation",
) -> pd.DataFrame:
    """Return all vintages published for a specific target hour (FR-3).

    Args:
        forecasts_df: WINDFOR snapshot DataFrame.
        target_time: Target delivery hour UTC datetime.
        generation_col: Column name for forecast MW.

    Returns:
        DataFrame sorted by publishTime ascending with horizon_h.
    """
    if forecasts_df.empty:
        return pd.DataFrame(columns=["publishTime", "forecast_mw", "horizon_h"])

    if not pd.api.types.is_datetime64_any_dtype(forecasts_df["startTime"]):
        df = forecasts_df.copy()
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    else:
        df = forecasts_df

    target_ts = pd.Timestamp(target_time)
    if target_ts.tzinfo is None:
        target_ts = target_ts.tz_localize("UTC")

    target_rows = df[df["startTime"] == target_ts].copy()
    if target_rows.empty:
        return pd.DataFrame(columns=["publishTime", "forecast_mw", "horizon_h"])

    if not pd.api.types.is_datetime64_any_dtype(target_rows["publishTime"]):
        target_rows["publishTime"] = pd.to_datetime(target_rows["publishTime"], utc=True)

    target_rows = target_rows.rename(columns={generation_col: "forecast_mw"})
    target_rows["horizon_h"] = (
        target_rows["startTime"] - target_rows["publishTime"]
    ).dt.total_seconds() / 3600.0

    cols = ["publishTime", "forecast_mw", "horizon_h"]
    return target_rows[cols].sort_values("publishTime").reset_index(drop=True)
