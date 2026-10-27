"""Health check router."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import APP_VERSION

router = APIRouter(tags=["meta"])


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        timestamp=datetime.now(UTC).isoformat(),
    )
