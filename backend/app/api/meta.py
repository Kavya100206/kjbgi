"""Snapshot metadata endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.data.loader import load_actuals, load_forecasts, load_meta

router = APIRouter(tags=["meta"])


@router.get("/meta")
def get_metadata() -> dict[str, Any]:
    """Return snapshot metadata and confirm data is loaded via pandas."""
    meta = load_meta()
    act = load_actuals()
    fc = load_forecasts()

    return {
        "status": "ready",
        "ingested_at": meta.get("ingested_at"),
        "window": meta.get("window"),
        "actuals_rows_loaded": len(act),
        "forecasts_rows_loaded": len(fc),
        "total_compressed_size_kb": meta.get("total_compressed_size_kb"),
    }
