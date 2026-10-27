"""Accuracy endpoints: summary, by-horizon, by-hour, daily, and distribution."""

from __future__ import annotations

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Query, Response

from app.api.deps import validate_cutoff_hour, validate_date_range
from app.api.schemas import (
    AccuracyByHorizonResponse,
    AccuracyByHourResponse,
    AccuracyDailyResponse,
    AccuracyDistributionResponse,
    AccuracySummaryResponse,
    DailyMetricItem,
    DistributionBinItem,
    HorizonBucketItem,
    HourMetricItem,
)
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

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


@router.get("/summary", response_model=AccuracySummaryResponse)
def get_accuracy_summary(
    response: Response,
    from_date: Annotated[str, Query(description="Start delivery date (YYYY-MM-DD)")] = "2026-01-01",
    to_date: Annotated[str, Query(description="End delivery date (YYYY-MM-DD)")] = "2026-01-31",
    cutoff_hour: Annotated[
        int, Query(ge=0, le=23, description="Decision cutoff hour (0..23 UTC)")
    ] = 9,
) -> AccuracySummaryResponse:
    """Return headline accuracy metrics (MAE, RMSE, bias, error_std, ratio, bias_share_of_mse)."""
    response.headers["Cache-Control"] = "public, max-age=3600"

    d_start, d_end = validate_date_range(from_date, to_date)
    validate_cutoff_hour(cutoff_hour)

    forecasts_raw = load_forecasts()
    actuals_raw = load_actuals()

    # Select decision-time forecasts in window
    selected_fc = select_forecasts_at_cutoff(
        forecasts_df=forecasts_raw,
        cutoff_hour=cutoff_hour,
        start_date=d_start,
        end_date=d_end,
    )

    paired = pair_forecast_and_actual(selected_fc, actuals_raw)

    # Denominator = 24 target hours * number of delivery days in range
    num_days = (d_end - d_start).days + 1
    expected_denominator = num_days * 24

    metrics = compute_metrics_dict(
        errors=paired["error_mw"],
        actuals=paired["actual_mw"],
        forecasts=paired["forecast_mw"],
        denominator=expected_denominator,
    )

    return AccuracySummaryResponse(
        from_date=d_start.isoformat(),
        to_date=d_end.isoformat(),
        cutoff_hour=cutoff_hour,
        n=metrics["n"],
        denominator=metrics["denominator"],
        coverage_pct=metrics["coverage_pct"],
        mae_mw=metrics["mae_mw"],
        rmse_mw=metrics["rmse_mw"],
        bias_mw=metrics["bias_mw"],
        error_std_mw=metrics["error_std_mw"],
        nmae_pct=metrics["nmae_pct"],
        mean_actual_mw=metrics["mean_actual_mw"],
        mean_forecast_mw=metrics["mean_forecast_mw"],
        forecast_to_actual_ratio=metrics["forecast_to_actual_ratio"],
        bias_share_of_mse=metrics["bias_share_of_mse"],
        p50_abs_error_mw=metrics["p50_abs_error_mw"],
        p90_abs_error_mw=metrics["p90_abs_error_mw"],
        p95_abs_error_mw=metrics["p95_abs_error_mw"],
        p90_over_forecast_mw=metrics["p90_over_forecast_mw"],
        worst_over_forecast_mw=metrics["worst_over_forecast_mw"],
    )


@router.get("/by-horizon", response_model=AccuracyByHorizonResponse)
def get_accuracy_by_horizon(
    response: Response,
    from_date: Annotated[str, Query(description="Start delivery date (YYYY-MM-DD)")] = "2026-01-01",
    to_date: Annotated[str, Query(description="End delivery date (YYYY-MM-DD)")] = "2026-01-31",
) -> AccuracyByHorizonResponse:
    """Evaluate accuracy over ALL forward vintages bucketed by lead time (FR-5)."""
    response.headers["Cache-Control"] = "public, max-age=3600"

    d_start, d_end = validate_date_range(from_date, to_date)

    forecasts_raw = load_forecasts()
    actuals_raw = load_actuals()

    # Filter forecasts whose target startTime is within [from_date, to_date]
    start_ts = pd.Timestamp(f"{d_start.isoformat()}T00:00:00Z")
    end_ts = pd.Timestamp(f"{d_end.isoformat()}T23:59:59Z")
    fc_filtered = forecasts_raw[
        (forecasts_raw["startTime"] >= start_ts) & (forecasts_raw["startTime"] <= end_ts)
    ]

    horizon_data = aggregate_by_horizon(fc_filtered, actuals_raw)

    buckets = [
        HorizonBucketItem(
            bucket=b["bucket"],
            n=b["n"],
            mean_forecast_mw=b["mean_forecast_mw"],
            mean_actual_mw=b["mean_actual_mw"],
            bias_mw=b["bias_mw"],
            mae_mw=b["mae_mw"],
            rmse_mw=b["rmse_mw"],
        )
        for b in horizon_data["buckets"]
    ]

    return AccuracyByHorizonResponse(
        from_date=d_start.isoformat(),
        to_date=d_end.isoformat(),
        total_vintages_evaluated=horizon_data["total_evaluated_count"],
        excluded_backcasts_count=horizon_data["excluded_backcasts_count"],
        buckets=buckets,
    )


@router.get("/by-hour", response_model=AccuracyByHourResponse)
def get_accuracy_by_hour(
    response: Response,
    from_date: Annotated[str, Query(description="Start delivery date (YYYY-MM-DD)")] = "2026-01-01",
    to_date: Annotated[str, Query(description="End delivery date (YYYY-MM-DD)")] = "2026-01-31",
    cutoff_hour: Annotated[
        int, Query(ge=0, le=23, description="Decision cutoff hour (0..23 UTC)")
    ] = 9,
) -> AccuracyByHourResponse:
    """Group paired decision-time forecasts by hour of day (0..23 UTC)."""
    response.headers["Cache-Control"] = "public, max-age=3600"

    d_start, d_end = validate_date_range(from_date, to_date)
    validate_cutoff_hour(cutoff_hour)

    forecasts_raw = load_forecasts()
    actuals_raw = load_actuals()

    selected_fc = select_forecasts_at_cutoff(
        forecasts_df=forecasts_raw,
        cutoff_hour=cutoff_hour,
        start_date=d_start,
        end_date=d_end,
    )
    paired = pair_forecast_and_actual(selected_fc, actuals_raw)
    hour_rows = aggregate_by_hour(paired)

    num_days = (d_end - d_start).days + 1

    hours = [
        HourMetricItem(
            hour=h["hour"],
            mean_forecast_mw=h["mean_forecast_mw"],
            mean_actual_mw=h["mean_actual_mw"],
            bias_mw=h["bias_mw"],
            mae_mw=h["mae_mw"],
            rmse_mw=h["rmse_mw"],
            n=h["n"],
            coverage_pct=round((h["n"] / num_days) * 100.0, 1) if num_days > 0 else 0.0,
        )
        for h in hour_rows
    ]

    confounding_note = (
        f"Confounded lead-time effect: from a fixed {cutoff_hour:02d}:00 UTC decision cutoff on D-1, forecast lead time naturally increases "
        f"across the delivery day (~16.5h for hour 00 to ~39.5h for hour 23). Variations by hour reflect both diurnal wind patterns and forecast lead-time decay."
    )

    return AccuracyByHourResponse(
        from_date=d_start.isoformat(),
        to_date=d_end.isoformat(),
        cutoff_hour=cutoff_hour,
        lead_time_confounding_note=confounding_note,
        hours=hours,
    )


@router.get("/daily", response_model=AccuracyDailyResponse)
def get_accuracy_daily(
    response: Response,
    from_date: Annotated[str, Query(description="Start delivery date (YYYY-MM-DD)")] = "2026-01-01",
    to_date: Annotated[str, Query(description="End delivery date (YYYY-MM-DD)")] = "2026-01-31",
    cutoff_hour: Annotated[
        int, Query(ge=0, le=23, description="Decision cutoff hour (0..23 UTC)")
    ] = 9,
) -> AccuracyDailyResponse:
    """Group paired decision-time forecasts by delivery day."""
    response.headers["Cache-Control"] = "public, max-age=3600"

    d_start, d_end = validate_date_range(from_date, to_date)
    validate_cutoff_hour(cutoff_hour)

    forecasts_raw = load_forecasts()
    actuals_raw = load_actuals()

    selected_fc = select_forecasts_at_cutoff(
        forecasts_df=forecasts_raw,
        cutoff_hour=cutoff_hour,
        start_date=d_start,
        end_date=d_end,
    )
    paired = pair_forecast_and_actual(selected_fc, actuals_raw)
    daily_rows = aggregate_daily(paired)

    days = [
        DailyMetricItem(
            date=d["date"],
            mean_forecast_mw=d["mean_forecast_mw"],
            mean_actual_mw=d["mean_actual_mw"],
            bias_mw=d["bias_mw"],
            mae_mw=d["mae_mw"],
            rmse_mw=d["rmse_mw"],
            n=d["n"],
            coverage_pct=d["coverage_pct"],
        )
        for d in daily_rows
    ]

    return AccuracyDailyResponse(
        from_date=d_start.isoformat(),
        to_date=d_end.isoformat(),
        cutoff_hour=cutoff_hour,
        days=days,
    )


@router.get("/distribution", response_model=AccuracyDistributionResponse)
def get_accuracy_distribution(
    response: Response,
    from_date: Annotated[str, Query(description="Start delivery date (YYYY-MM-DD)")] = "2026-01-01",
    to_date: Annotated[str, Query(description="End delivery date (YYYY-MM-DD)")] = "2026-01-31",
    cutoff_hour: Annotated[
        int, Query(ge=0, le=23, description="Decision cutoff hour (0..23 UTC)")
    ] = 9,
    bins: Annotated[int, Query(ge=5, le=50, description="Number of histogram bins")] = 20,
) -> AccuracyDistributionResponse:
    """Return error distribution histogram, empirical quantiles, and plain-English reading."""
    response.headers["Cache-Control"] = "public, max-age=3600"

    d_start, d_end = validate_date_range(from_date, to_date)
    validate_cutoff_hour(cutoff_hour)

    forecasts_raw = load_forecasts()
    actuals_raw = load_actuals()

    selected_fc = select_forecasts_at_cutoff(
        forecasts_df=forecasts_raw,
        cutoff_hour=cutoff_hour,
        start_date=d_start,
        end_date=d_end,
    )
    paired = pair_forecast_and_actual(selected_fc, actuals_raw)
    dist = aggregate_distribution(paired, num_bins=bins)

    bin_items = [
        DistributionBinItem(
            bin_start=b["bin_start"],
            bin_end=b["bin_end"],
            bin_mid=b["bin_mid"],
            count=b["count"],
            pct=b["pct_of_total"],
        )
        for b in dist["bins"]
    ]

    reading = dist.get("plain_english_p90") or "Insufficient data to compute error reading."

    return AccuracyDistributionResponse(
        from_date=d_start.isoformat(),
        to_date=d_end.isoformat(),
        cutoff_hour=cutoff_hour,
        num_samples=dist["total_count"],
        bins=bin_items,
        quantiles=dist["quantiles"],
        plain_english_reading=reading,
    )
