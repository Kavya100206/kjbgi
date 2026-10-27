"""Risk endpoints: empirical risk cushion bands."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import parse_iso_date, validate_confidence, validate_cutoff_hour
from app.api.schemas import RiskBandHourItem, RiskBandResponse
from app.data.loader import load_actuals, load_forecasts
from app.domain.pairing import pair_forecast_and_actual
from app.domain.risk import compute_risk_band
from app.domain.vintage import select_forecasts_at_cutoff

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/band", response_model=RiskBandResponse)
def get_risk_band(
    response: Response,
    date: Annotated[str, Query(description="Delivery date (YYYY-MM-DD)")] = "2026-01-15",
    cutoff_hour: Annotated[
        int, Query(ge=0, le=23, description="Decision cutoff hour (0..23 UTC)")
    ] = 9,
    confidence: Annotated[
        float, Query(ge=0.50, le=0.99, description="Confidence interval (0.50..0.99)")
    ] = 0.80,
) -> RiskBandResponse:
    """Return empirical risk buffer bands and MW cushion derived strictly from prior days."""
    response.headers["Cache-Control"] = "public, max-age=3600"

    deliv_date = parse_iso_date(date, "date")
    validate_cutoff_hour(cutoff_hour)
    validate_confidence(confidence)

    forecasts_raw = load_forecasts()
    actuals_raw = load_actuals()

    # Select all decision-time forecasts up through delivery date
    all_selected = select_forecasts_at_cutoff(
        forecasts_df=forecasts_raw,
        cutoff_hour=cutoff_hour,
    )
    paired_history = pair_forecast_and_actual(all_selected, actuals_raw)

    # Day forecasts for delivery date D
    day_fc = select_forecasts_at_cutoff(
        forecasts_df=forecasts_raw,
        cutoff_hour=cutoff_hour,
        delivery_date=deliv_date,
    )

    band_data = compute_risk_band(
        delivery_date=deliv_date,
        cutoff_hour=cutoff_hour,
        paired_history_df=paired_history,
        day_forecasts_df=day_fc,
        confidence=confidence,
    )

    hours = [
        RiskBandHourItem(
            start_time=h["startTime"],
            hour=h["hour"],
            forecast_mw=h["forecast_mw"],
            band_lo_mw=h["band_lo_mw"],
            band_hi_mw=h["band_hi_mw"],
            cushion_mw=h["cushion_mw"],
            bias_used_mw=h.get("bias_used_mw", 0.0),
        )
        for h in band_data["hours"]
    ]

    return RiskBandResponse(
        delivery_date=band_data["delivery_date"],
        cutoff_hour=band_data["cutoff_hour"],
        confidence=band_data["confidence"],
        history_days_used=band_data["history_days_used"],
        is_fallback=band_data["is_fallback"],
        bias_used_mw=band_data["bias_used_mw"],
        hours=hours,
    )
