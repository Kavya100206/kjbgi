"""Data loader module — loads and validates committed snapshots into typed DataFrames.

Validates schemas strictly, parses UTC datetimes, computes derived columns,
and fails loudly with descriptive ValueError on missing columns or invalid data.
"""

from __future__ import annotations

import functools
import json
import pathlib
from typing import Any

import pandas as pd

from app.config import ACTUALS_PATH, FORECASTS_PATH, META_PATH

# Required columns per dataset
FUELHH_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    [
        "dataset",
        "publishTime",
        "startTime",
        "settlementDate",
        "settlementPeriod",
        "fuelType",
        "generation",
    ]
)

WINDFOR_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    [
        "dataset",
        "publishTime",
        "startTime",
        "generation",
    ]
)

META_REQUIRED_KEYS: frozenset[str] = frozenset(
    [
        "ingested_at",
        "window",
        "actuals",
        "forecasts",
    ]
)


def validate_dataframe_schema(
    df: pd.DataFrame,
    required_columns: frozenset[str],
    dataset_name: str,
) -> None:
    """Validate that DataFrame contains all required columns and is not empty.

    Raises:
        ValueError: If DataFrame is empty or missing any required column.
    """
    if df.empty:
        raise ValueError(f"Loaded {dataset_name} dataset is empty")

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(
            f"Schema validation failed for {dataset_name}: missing required columns: {sorted(missing)}"
        )


def load_actuals(path: pathlib.Path | str | None = None) -> pd.DataFrame:
    """Load FUELHH wind actuals from gzipped CSV, validate schema, and parse UTC dates.

    Args:
        path: Path to actuals.csv.gz (defaults to config.ACTUALS_PATH).

    Returns:
        pd.DataFrame with UTC datetime startTime and publishTime, sorted by startTime.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If schema validation fails or data contains negative generation.
    """
    target_path = pathlib.Path(path) if path is not None else ACTUALS_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Actuals snapshot file not found: {target_path}")

    df = pd.read_csv(target_path, compression="gzip" if str(target_path).endswith(".gz") else None)
    validate_dataframe_schema(df, FUELHH_REQUIRED_COLUMNS, "FUELHH")

    if (df["generation"] < 0).any():
        raise ValueError("FUELHH dataset contains negative generation values")

    # Parse UTC timestamps
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = df["generation"].astype(int)
    df["settlementPeriod"] = df["settlementPeriod"].astype(int)

    return df.sort_values("startTime").reset_index(drop=True)


def load_forecasts(path: pathlib.Path | str | None = None) -> pd.DataFrame:
    """Load WINDFOR wind forecasts from gzipped CSV, validate schema, and compute horizon.

    Args:
        path: Path to forecasts.csv.gz (defaults to config.FORECASTS_PATH).

    Returns:
        pd.DataFrame with UTC datetime startTime, publishTime, and derived horizon_h.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If schema validation fails or data contains negative generation.
    """
    target_path = pathlib.Path(path) if path is not None else FORECASTS_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Forecasts snapshot file not found: {target_path}")

    df = pd.read_csv(target_path, compression="gzip" if str(target_path).endswith(".gz") else None)
    validate_dataframe_schema(df, WINDFOR_REQUIRED_COLUMNS, "WINDFOR")

    if (df["generation"] < 0).any():
        raise ValueError("WINDFOR dataset contains negative generation values")

    # Parse UTC timestamps
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["generation"] = df["generation"].astype(int)

    # Derived horizon in hours: (startTime - publishTime)
    df["horizon_h"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600.0

    return df.sort_values(["publishTime", "startTime"]).reset_index(drop=True)


def load_meta(path: pathlib.Path | str | None = None) -> dict[str, Any]:
    """Load and validate snapshot metadata from JSON.

    Args:
        path: Path to meta.json (defaults to config.META_PATH).

    Returns:
        Validated dict containing metadata.

    Raises:
        FileNotFoundError: If meta.json does not exist.
        ValueError: If required metadata keys are missing.
    """
    target_path = pathlib.Path(path) if path is not None else META_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {target_path}")

    with open(target_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected metadata to be a JSON object, got {type(data)}")

    missing = META_REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Metadata missing required keys: {sorted(missing)}")

    return data


# ── In-Memory Cached Accessors for API Performance ────────────────────────────


@functools.lru_cache(maxsize=1)
def get_cached_actuals() -> pd.DataFrame:
    """Return in-memory cached copy of actuals DataFrame."""
    return load_actuals()


@functools.lru_cache(maxsize=1)
def get_cached_forecasts() -> pd.DataFrame:
    """Return in-memory cached copy of forecasts DataFrame."""
    return load_forecasts()


@functools.lru_cache(maxsize=1)
def get_cached_meta() -> dict[str, Any]:
    """Return in-memory cached snapshot metadata."""
    return load_meta()


def clear_loader_cache() -> None:
    """Clear all in-memory snapshot caches (useful in test suites)."""
    get_cached_actuals.cache_clear()
    get_cached_forecasts.cache_clear()
    get_cached_meta.cache_clear()
