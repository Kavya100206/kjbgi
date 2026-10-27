"""Forecast endpoints: daily forecast-at-decision and vintage revisions."""

from __future__ import annotations

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import parse_iso_date, validate_cutoff_hour
from app.api.schemas import (
    ForecastDayResponse,
    ForecastHourItem,
    ForecastRevisionsResponse,
    RevisionVintageItem,
)
from app.data.loader import load_actuals, load_forecasts
from app.domain.pairing import compute_hourly_actuals, pair_forecast_and_actual
from app.domain.vintage import (
    get_cutoff_for_target,
    get_vintage_revisions_for_target,
    select_forecasts_at_cutoff,
)

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/day", response_model=ForecastDayResponse)
def get_forecast_day(
    response: Response,
    date: Annotated[str, Query(description="Delivery date (YYYY-MM-DD)")] = "2026-01-15",
    cutoff_hour: Annotated[
        int, Query(ge=0, le=23, description="Decision cutoff hour (0..23 UTC)")
    ] = 9,
) -> ForecastDayResponse:
    """Return 24-hour forecast at decision cutoff with paired actuals and day summary."""
    response.headers["Cache-Control"] = "public, max-age=3600"

    deliv_date = parse_iso_date(date, "date")
    validate_cutoff_hour(cutoff_hour)

    forecasts_raw = load_forecasts()
    actuals_raw = load_actuals()

    # Select decision-time forecasts for this delivery date
    selected_fc = select_forecasts_at_cutoff(
        forecasts_df=forecasts_raw,
        cutoff_hour=cutoff_hour,
        delivery_date=deliv_date,
    )

    if selected_fc.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No forecast vintages found for delivery date {deliv_date} at cutoff {cutoff_hour:02d}:00 UTC",
        )

    # Pair with hourly actuals per A7
    paired = pair_forecast_and_actual(selected_fc, actuals_raw)

    rows: list[ForecastHourItem] = []
    selected_vintages_set: set[str] = set()

    for _, r in paired.iterrows():
        t = pd.Timestamp(r["startTime"])
        pub_t = pd.Timestamp(r["publishTime"])
        pub_str = pub_t.strftime("%Y-%m-%dT%H:%M:%SZ")
        selected_vintages_set.add(pub_str)

        act_val = float(r["actual_mw"]) if pd.notna(r.get("actual_mw")) else None
        err_val = float(r["error_mw"]) if pd.notna(r.get("error_mw")) else None

        rows.append(
            ForecastHourItem(
                start_time=t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                hour=t.hour,
                forecast_mw=round(float(r["forecast_mw"]), 1),
                publish_time=pub_str,
                forecast_age_h=round(float(r["forecast_age_h"]), 2),
                actual_mw=round(act_val, 1) if act_val is not None else None,
                error_mw=round(err_val, 1) if err_val is not None else None,
            )
        )

    # Sort by hour 0..23
    rows.sort(key=lambda x: x.hour)

    forecast_vals = [r.forecast_mw for r in rows]
    actual_vals = [r.actual_mw for r in rows if r.actual_mw is not None]

    peak_fc = max(forecast_vals) if forecast_vals else 0.0
    mean_fc = sum(forecast_vals) / len(forecast_vals) if forecast_vals else 0.0
    min_fc = min(forecast_vals) if forecast_vals else 0.0
    mean_act = (sum(actual_vals) / len(actual_vals)) if actual_vals else None

    # Latest selected vintage among the 24 hours
    selected_vintage_pub = max(selected_vintages_set) if selected_vintages_set else ""

    return ForecastDayResponse(
        delivery_date=deliv_date.isoformat(),
        cutoff_hour=cutoff_hour,
        selected_vintage_publish_time=selected_vintage_pub,
        peak_forecast_mw=round(peak_fc, 1),
        mean_forecast_mw=round(mean_fc, 1),
        min_forecast_mw=round(min_fc, 1),
        mean_actual_mw=round(mean_act, 1) if mean_act is not None else None,
        n_missing=24 - len(rows),
        rows=rows,
    )


@router.get("/revisions", response_model=ForecastRevisionsResponse)
def get_forecast_revisions(
    response: Response,
    target: Annotated[
        str | None, Query(description="Target delivery timestamp (ISO-8601 UTC)")
    ] = None,
    date: Annotated[
        str | None, Query(description="Delivery date (defaults target to 12:00Z)")
    ] = None,
    cutoff_hour: Annotated[
        int, Query(ge=0, le=23, description="Decision cutoff hour for labelling")
    ] = 9,
) -> ForecastRevisionsResponse:
    """Return historical vintages for a given target delivery hour to inspect forecast revisions."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    validate_cutoff_hour(cutoff_hour)

    if target is not None:
        try:
            target_dt = pd.to_datetime(target, utc=True)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid target timestamp: '{target}'",
            ) from err
    elif date is not None:
        deliv_date = parse_iso_date(date, "date")
        target_dt = pd.Timestamp(f"{deliv_date.isoformat()}T12:00:00Z")
    else:
        # Default to 2026-01-15T12:00:00Z
        target_dt = pd.Timestamp("2026-01-15T12:00:00Z")

    forecasts_raw = load_forecasts()
    actuals_raw = load_actuals()

    # Decision cutoff time for this target delivery hour
    cutoff_dt = get_cutoff_for_target(target_dt.to_pydatetime(), cutoff_hour)

    rev_df = get_vintage_revisions_for_target(forecasts_raw, target_dt)
    if rev_df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No forecast vintages found for target time {target_dt.isoformat()}",
        )

    # Compute hourly actual for target if available
    hourly_acts = compute_hourly_actuals(actuals_raw)
    target_act = hourly_acts[hourly_acts["startTime"] == target_dt]
    act_mw: float | None = None
    if not target_act.empty and pd.notna(target_act.iloc[0]["actual_mw"]):
        act_mw = round(float(target_act.iloc[0]["actual_mw"]), 1)

    vintages: list[RevisionVintageItem] = []
    for _, r in rev_df.iterrows():
        pub_t = pd.Timestamp(r["publishTime"])
        age_h = round((cutoff_dt - pub_t.to_pydatetime()).total_seconds() / 3600.0, 2)
        is_before = pub_t <= pd.Timestamp(cutoff_dt)

        vintages.append(
            RevisionVintageItem(
                publish_time=pub_t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                forecast_mw=round(float(r["forecast_mw"]), 1),
                horizon_h=round(float(r["horizon_h"]), 1),
                forecast_age_h=age_h if is_before else None,
                is_before_cutoff=is_before,
            )
        )

    return ForecastRevisionsResponse(
        target_start_time=target_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        delivery_date=target_dt.strftime("%Y-%m-%d"),
        cutoff_hour=cutoff_hour,
        actual_mw=act_mw,
        vintages=vintages,
    )
