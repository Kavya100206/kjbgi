"""Ingest script for Elexon BMRS FUELHH (WIND) and WINDFOR datasets.

Fetches data in 7-day chunks with polite delay and retry/backoff, validates records
against Pydantic schemas, deduplicates per assumption A6, and writes byte-identical
deterministic compressed snapshots (gzip mtime=0) to disk with metadata.
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import pathlib
import sys
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

import httpx
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

# Ensure backend directory is in sys.path
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import (  # noqa: E402
    ACTUALS_DATE_FROM,
    ACTUALS_DATE_TO,
    DEFAULT_CUTOFF_HOUR,
    ELEXON_BASE_URL,
    FORECASTS_PUBLISH_FROM,
    FORECASTS_PUBLISH_TO,
    INGEST_CHUNK_DAYS,
    INGEST_DELAY_S,
    SNAPSHOT_DIR,
    WINDOW_END,
    WINDOW_START,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("ingest")


# ── Pydantic Schemas ──────────────────────────────────────────────────────────


class FuelHHRecord(BaseModel):
    """Single 30-minute FUELHH actual record."""

    model_config = ConfigDict(extra="ignore")

    dataset: Literal["FUELHH"]
    publishTime: datetime
    startTime: datetime
    settlementDate: str
    settlementPeriod: int = Field(ge=1, le=50)
    fuelType: str
    generation: int = Field(ge=0)


class WindforRecord(BaseModel):
    """Single hourly WINDFOR forecast record."""

    model_config = ConfigDict(extra="ignore")

    dataset: Literal["WINDFOR"]
    publishTime: datetime
    startTime: datetime
    generation: int = Field(ge=0)


FuelHHListAdapter: TypeAdapter[list[FuelHHRecord]] = TypeAdapter(list[FuelHHRecord])
WindforListAdapter: TypeAdapter[list[WindforRecord]] = TypeAdapter(list[WindforRecord])


# ── Deterministic Gzip Writer (mtime=0) ─────────────────────────────────────────


def write_deterministic_csv_gz(df: pd.DataFrame, target_path: pathlib.Path) -> None:
    """Write DataFrame to gzipped CSV with mtime=0 for byte-level reproducibility."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        open(target_path, "wb") as f_out,
        gzip.GzipFile(filename="", mode="wb", fileobj=f_out, mtime=0.0) as gz,
    ):
        df.to_csv(gz, index=False, lineterminator="\n", encoding="utf-8")


# ── HTTP Client with Retry / Backoff ──────────────────────────────────────────


def fetch_with_retry(
    client: httpx.Client,
    url: str,
    params: dict[str, str],
    max_retries: int = 3,
    backoff_factor: float = 1.0,
) -> list[dict[str, Any]]:
    """Fetch URL with exponential backoff on network errors or 429/5xx status."""
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            logger.info("GET %s params=%s (attempt %d/%d)", url, params, attempt + 1, max_retries)
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "data" in data:
                    return data["data"]
                raise ValueError(f"Unexpected response structure: {type(data)}")

            if resp.status_code in (429, 500, 502, 503, 504):
                wait_time = backoff_factor * (2**attempt)
                logger.warning(
                    "HTTP %d from %s, retrying in %.1fs...", resp.status_code, url, wait_time
                )
                time.sleep(wait_time)
                continue

            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            last_err = exc
            wait_time = backoff_factor * (2**attempt)
            logger.warning("Request failed (%s), retrying in %.1fs...", exc, wait_time)
            time.sleep(wait_time)

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts: {last_err}")


# ── Chunk Generator ───────────────────────────────────────────────────────────


def generate_date_chunks(
    start_date: date, end_date: date, chunk_days: int
) -> list[tuple[date, date]]:
    """Generate non-overlapping date intervals of at most chunk_days."""
    chunks = []
    curr = start_date
    while curr <= end_date:
        chunk_end = min(curr + timedelta(days=chunk_days - 1), end_date)
        chunks.append((curr, chunk_end))
        curr = chunk_end + timedelta(days=1)
    return chunks


def generate_datetime_chunks(
    start_dt: datetime, end_dt: datetime, chunk_days: int
) -> list[tuple[datetime, datetime]]:
    """Generate non-overlapping datetime intervals of at most chunk_days."""
    chunks = []
    curr = start_dt
    while curr <= end_dt:
        chunk_end = min(curr + timedelta(days=chunk_days) - timedelta(seconds=1), end_dt)
        chunks.append((curr, chunk_end))
        curr = chunk_end + timedelta(seconds=1)
    return chunks


# ── Dataset Fetchers ──────────────────────────────────────────────────────────


def fetch_fuelhh_actuals(
    client: httpx.Client,
    start_date: date = ACTUALS_DATE_FROM,
    end_date: date = ACTUALS_DATE_TO,
    chunk_days: int = INGEST_CHUNK_DAYS,
    delay_s: float = INGEST_DELAY_S,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Fetch FUELHH wind actuals chunked by settlementDate, validated with Pydantic."""
    url = f"{ELEXON_BASE_URL}/datasets/FUELHH/stream"
    chunks = generate_date_chunks(start_date, end_date, chunk_days)
    all_records: list[dict[str, Any]] = []
    total_fetched = 0
    total_rejected = 0

    for i, (chunk_start, chunk_end) in enumerate(chunks):
        params = {
            "settlementDateFrom": chunk_start.isoformat(),
            "settlementDateTo": chunk_end.isoformat(),
            "fuelType": "WIND",
        }
        raw_items = fetch_with_retry(client, url, params)
        total_fetched += len(raw_items)

        chunk_valid: list[FuelHHRecord] = []
        for raw in raw_items:
            try:
                item = FuelHHRecord.model_validate(raw)
                chunk_valid.append(item)
            except Exception as exc:
                total_rejected += 1
                logger.warning("Rejected FUELHH record: %s (error: %s)", raw, exc)

        logger.info(
            "Chunk %d/%d: retrieved %d valid FUELHH records (rejected %d)",
            i + 1,
            len(chunks),
            len(chunk_valid),
            total_rejected,
        )
        for item in chunk_valid:
            all_records.append(
                {
                    "dataset": item.dataset,
                    "publishTime": item.publishTime.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "startTime": item.startTime.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "settlementDate": item.settlementDate,
                    "settlementPeriod": item.settlementPeriod,
                    "fuelType": item.fuelType,
                    "generation": item.generation,
                }
            )
        if i < len(chunks) - 1:
            time.sleep(delay_s)

    df = pd.DataFrame(all_records)
    if df.empty:
        raise ValueError("No FUELHH records fetched")

    # Deduplicate exact duplicates (A6)
    initial_len = len(df)
    df = df.drop_duplicates(subset=["startTime", "fuelType"])
    duplicates_dropped = initial_len - len(df)
    if duplicates_dropped > 0:
        logger.info("Deduplicated FUELHH: %d -> %d rows", initial_len, len(df))

    # Deterministic sorting
    df = df.sort_values(["startTime", "settlementPeriod"]).reset_index(drop=True)
    stats = {
        "fetched": total_fetched,
        "valid": len(all_records),
        "rejected": total_rejected,
        "duplicates_dropped": duplicates_dropped,
        "kept": len(df),
    }
    return df, stats


def fetch_windfor_forecasts(
    client: httpx.Client,
    start_dt: datetime = FORECASTS_PUBLISH_FROM,
    end_dt: datetime = FORECASTS_PUBLISH_TO,
    chunk_days: int = INGEST_CHUNK_DAYS,
    delay_s: float = INGEST_DELAY_S,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Fetch WINDFOR wind forecasts chunked by publishDateTime, validated with Pydantic."""
    url = f"{ELEXON_BASE_URL}/datasets/WINDFOR/stream"
    chunks = generate_datetime_chunks(start_dt, end_dt, chunk_days)
    all_records: list[dict[str, Any]] = []
    total_fetched = 0
    total_rejected = 0

    for i, (chunk_start, chunk_end) in enumerate(chunks):
        params = {
            "publishDateTimeFrom": chunk_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        raw_items = fetch_with_retry(client, url, params)
        total_fetched += len(raw_items)

        chunk_valid: list[WindforRecord] = []
        for raw in raw_items:
            try:
                item = WindforRecord.model_validate(raw)
                chunk_valid.append(item)
            except Exception as exc:
                total_rejected += 1
                logger.warning("Rejected WINDFOR record: %s (error: %s)", raw, exc)

        logger.info(
            "Chunk %d/%d: retrieved %d valid WINDFOR records (rejected %d)",
            i + 1,
            len(chunks),
            len(chunk_valid),
            total_rejected,
        )
        for item in chunk_valid:
            all_records.append(
                {
                    "dataset": item.dataset,
                    "publishTime": item.publishTime.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "startTime": item.startTime.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "generation": item.generation,
                }
            )
        if i < len(chunks) - 1:
            time.sleep(delay_s)

    df = pd.DataFrame(all_records)
    if df.empty:
        raise ValueError("No WINDFOR records fetched")

    # Deduplicate exact duplicates on (publishTime, startTime)
    initial_len = len(df)
    df = df.drop_duplicates(subset=["publishTime", "startTime"])
    duplicates_dropped = initial_len - len(df)
    if duplicates_dropped > 0:
        logger.info("Deduplicated WINDFOR: %d -> %d rows", initial_len, len(df))

    # Deterministic sorting
    df = df.sort_values(["publishTime", "startTime"]).reset_index(drop=True)
    stats = {
        "fetched": total_fetched,
        "valid": len(all_records),
        "rejected": total_rejected,
        "duplicates_dropped": duplicates_dropped,
        "kept": len(df),
    }
    return df, stats


# ── Snapshot Writer ───────────────────────────────────────────────────────────


def write_snapshot(
    actuals_df: pd.DataFrame,
    forecasts_df: pd.DataFrame,
    snapshot_dir: pathlib.Path = SNAPSHOT_DIR,
    quality_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write actuals.csv.gz, forecasts.csv.gz, and meta.json with mtime=0."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    actuals_file = snapshot_dir / "actuals.csv.gz"
    forecasts_file = snapshot_dir / "forecasts.csv.gz"
    meta_file = snapshot_dir / "meta.json"

    write_deterministic_csv_gz(actuals_df, actuals_file)
    write_deterministic_csv_gz(forecasts_df, forecasts_file)

    actuals_size = actuals_file.stat().st_size
    forecasts_size = forecasts_file.stat().st_size
    total_size_kb = (actuals_size + forecasts_size) / 1024

    meta: dict[str, Any] = {
        "ingested_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {
            "start": WINDOW_START.isoformat(),
            "end": WINDOW_END.isoformat(),
            "default_cutoff_hour": DEFAULT_CUTOFF_HOUR,
        },
        "actuals": {
            "rows": len(actuals_df),
            "file": actuals_file.name,
            "size_bytes": actuals_size,
            "min_start_time": str(actuals_df["startTime"].min()),
            "max_start_time": str(actuals_df["startTime"].max()),
            "min_publish_time": str(actuals_df["publishTime"].min()),
            "max_publish_time": str(actuals_df["publishTime"].max()),
            "columns": list(actuals_df.columns),
        },
        "forecasts": {
            "rows": len(forecasts_df),
            "file": forecasts_file.name,
            "size_bytes": forecasts_size,
            "unique_vintages": int(forecasts_df["publishTime"].nunique()),
            "min_publish_time": str(forecasts_df["publishTime"].min()),
            "max_publish_time": str(forecasts_df["publishTime"].max()),
            "min_start_time": str(forecasts_df["startTime"].min()),
            "max_start_time": str(forecasts_df["startTime"].max()),
            "columns": list(forecasts_df.columns),
        },
        "total_compressed_size_kb": round(total_size_kb, 1),
    }

    if quality_stats:
        meta["ingest_quality"] = quality_stats

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info(
        "Snapshot written: actuals=%d rows (%d KB), forecasts=%d rows (%d KB), total=%.1f KB",
        len(actuals_df),
        actuals_size // 1024,
        len(forecasts_df),
        forecasts_size // 1024,
        total_size_kb,
    )
    return meta


# ── Main Entrypoint ───────────────────────────────────────────────────────────


def run_ingest(refresh: bool = False, target_dir: pathlib.Path = SNAPSHOT_DIR) -> dict[str, Any]:
    """Run ingest workflow, idempotent unless refresh=True."""
    actuals_file = target_dir / "actuals.csv.gz"
    forecasts_file = target_dir / "forecasts.csv.gz"
    meta_file = target_dir / "meta.json"

    if not refresh and actuals_file.exists() and forecasts_file.exists() and meta_file.exists():
        logger.info(
            "Existing snapshot found in %s and --refresh not specified; idempotent skip.",
            target_dir,
        )
        with open(meta_file, encoding="utf-8") as f:
            return json.load(f)

    logger.info("Starting data ingest (refresh=%s, target_dir=%s)...", refresh, target_dir)
    with httpx.Client(timeout=60.0) as client:
        actuals_df, actuals_stats = fetch_fuelhh_actuals(client)
        forecasts_df, forecasts_stats = fetch_windfor_forecasts(client)

    quality_stats = {
        "fuelhh": actuals_stats,
        "windfor": forecasts_stats,
    }

    meta = write_snapshot(actuals_df, forecasts_df, target_dir, quality_stats=quality_stats)
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Elexon FUELHH and WINDFOR data.")
    parser.add_argument(
        "--refresh", action="store_true", help="Force refresh even if snapshot exists"
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=SNAPSHOT_DIR,
        help="Target directory for snapshot files",
    )
    args = parser.parse_args()

    meta = run_ingest(refresh=args.refresh, target_dir=args.output_dir)
    print("\nIngest complete:")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
