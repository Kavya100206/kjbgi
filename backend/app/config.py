"""App configuration — window, default cutoff, constants."""

import pathlib
from datetime import UTC, date, datetime

# ── Ingest window ──────────────────────────────────────────────────────────────
# Target delivery hours: 2026-01-01T00:00Z … 2026-01-31T23:00Z
WINDOW_START: date = date(2026, 1, 1)
WINDOW_END: date = date(2026, 1, 31)

# Wider ingest range for actuals (up to Feb 1) and forecasts (from Dec 29)
ACTUALS_DATE_FROM: date = date(2026, 1, 1)
ACTUALS_DATE_TO: date = date(2026, 2, 1)  # inclusive of Feb 1 for completeness
FORECASTS_PUBLISH_FROM: datetime = datetime(2025, 12, 29, 0, 0, 0, tzinfo=UTC)
FORECASTS_PUBLISH_TO: datetime = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)

# ── Decision cutoff (A2) ──────────────────────────────────────────────────────
DEFAULT_CUTOFF_HOUR: int = 9  # 09:00 UTC; January = GMT so this is UK local time

# ── API ───────────────────────────────────────────────────────────────────────
APP_VERSION: str = "0.1.0"
APP_TITLE: str = "Vane — Wind Forecast Accuracy Portal"

# ── Elexon BMRS ───────────────────────────────────────────────────────────────
ELEXON_BASE_URL: str = "https://data.elexon.co.uk/bmrs/api/v1"
INGEST_CHUNK_DAYS: int = 7  # WINDFOR fetch window per request
INGEST_DELAY_S: float = 0.5  # polite delay between requests

# ── Snapshot paths ────────────────────────────────────────────────────────────
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def get_snapshot_dir() -> pathlib.Path:
    import os

    if env_val := os.getenv("SNAPSHOT_DIR"):
        return pathlib.Path(env_val)
    candidate1 = pathlib.Path(__file__).resolve().parent.parent / "data" / "snapshot"
    if candidate1.exists():
        return candidate1
    candidate2 = REPO_ROOT / "backend" / "data" / "snapshot"
    if candidate2.exists():
        return candidate2
    return candidate1


SNAPSHOT_DIR: pathlib.Path = get_snapshot_dir()
ACTUALS_PATH: pathlib.Path = SNAPSHOT_DIR / "actuals.csv.gz"
FORECASTS_PATH: pathlib.Path = SNAPSHOT_DIR / "forecasts.csv.gz"
META_PATH: pathlib.Path = SNAPSHOT_DIR / "meta.json"
