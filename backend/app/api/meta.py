"""Snapshot metadata endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.schemas import MetaResponse, WindowInfo
from app.data.loader import load_actuals, load_forecasts, load_meta

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def get_metadata(response: Response) -> MetaResponse:
    """Return snapshot metadata and available January 2026 dates."""
    response.headers["Cache-Control"] = "public, max-age=3600"

    meta = load_meta()
    act = load_actuals()
    fc = load_forecasts()

    # Generate full 31 dates in January 2026
    delivery_dates = [f"2026-01-{d:02d}" for d in range(1, 32)]

    return MetaResponse(
        status="ready",
        ingested_at=meta["ingested_at"],
        window=WindowInfo(
            start=meta["window"]["start"],
            end=meta["window"]["end"],
            default_cutoff_hour=int(meta["window"]["default_cutoff_hour"]),
        ),
        default_cutoff_hour=int(meta["window"].get("default_cutoff_hour", 9)),
        available_delivery_dates=delivery_dates,
        actuals_rows=len(act),
        forecasts_rows=len(fc),
        total_compressed_size_kb=float(meta["total_compressed_size_kb"]),
    )
