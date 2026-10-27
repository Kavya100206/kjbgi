"""Tests for scripts/ingest.py — chunking, Pydantic schemas, deduplication, and idempotence."""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, date, datetime

import pandas as pd
import pytest
from pydantic import ValidationError

from scripts.ingest import (
    FuelHHListAdapter,
    FuelHHRecord,
    WindforListAdapter,
    WindforRecord,
    generate_date_chunks,
    generate_datetime_chunks,
    run_ingest,
    write_snapshot,
)

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def test_generate_date_chunks_covers_range():
    start = date(2026, 1, 1)
    end = date(2026, 2, 1)  # 32 days
    chunks = generate_date_chunks(start, end, chunk_days=7)

    assert len(chunks) == 5
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 7))
    assert chunks[1] == (date(2026, 1, 8), date(2026, 1, 14))
    assert chunks[-1] == (date(2026, 1, 29), date(2026, 2, 1))

    # Verify continuity and no gaps
    for i in range(len(chunks) - 1):
        assert (chunks[i + 1][0] - chunks[i][1]).days == 1


def test_generate_datetime_chunks_covers_range():
    start = datetime(2025, 12, 29, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
    chunks = generate_datetime_chunks(start, end, chunk_days=7)

    assert len(chunks) == 5
    assert chunks[0][0] == start
    assert chunks[-1][1] == end

    for i in range(len(chunks) - 1):
        gap = (chunks[i + 1][0] - chunks[i][1]).total_seconds()
        assert gap == 1.0


def test_fuelhh_validation_with_real_fixture():
    fixture_path = FIXTURES_DIR / "fuelhh_jan15_sample.json"
    assert fixture_path.exists()

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    validated = FuelHHListAdapter.validate_python(data)
    assert len(validated) == 48
    first = validated[0]
    assert first.dataset == "FUELHH"
    assert first.fuelType == "WIND"
    assert first.generation >= 0
    assert 1 <= first.settlementPeriod <= 48


def test_fuelhh_validation_rejects_invalid_records():
    # Negative generation
    with pytest.raises(ValidationError):
        FuelHHRecord.model_validate(
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T01:00:00Z",
                "startTime": "2026-01-15T00:30:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 2,
                "fuelType": "WIND",
                "generation": -5,
            }
        )

    # Invalid dataset name
    with pytest.raises(ValidationError):
        FuelHHRecord.model_validate(
            {
                "dataset": "OTHER",
                "publishTime": "2026-01-15T01:00:00Z",
                "startTime": "2026-01-15T00:30:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 2,
                "fuelType": "WIND",
                "generation": 100,
            }
        )


def test_windfor_validation_with_real_fixture():
    fixture_path = FIXTURES_DIR / "windfor_publishdt_jan14_sample.json"
    assert fixture_path.exists()

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    validated = WindforListAdapter.validate_python(data)
    assert len(validated) == 584
    first = validated[0]
    assert first.dataset == "WINDFOR"
    assert first.generation >= 0


def test_windfor_validation_rejects_invalid_records():
    # Negative generation
    with pytest.raises(ValidationError):
        WindforRecord.model_validate(
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-14T02:30:00Z",
                "startTime": "2026-01-13T21:00:00Z",
                "generation": -10,
            }
        )

    # Invalid dataset name
    with pytest.raises(ValidationError):
        WindforRecord.model_validate(
            {
                "dataset": "NOT_WINDFOR",
                "publishTime": "2026-01-14T02:30:00Z",
                "startTime": "2026-01-13T21:00:00Z",
                "generation": 500,
            }
        )


def test_write_snapshot_and_idempotence(tmp_path):
    # Prepare dummy dataframes
    actuals = pd.DataFrame(
        [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 5000,
            }
        ]
    )
    forecasts = pd.DataFrame(
        [
            {
                "dataset": "WINDFOR",
                "publishTime": "2025-12-31T07:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "generation": 5200,
            }
        ]
    )

    meta = write_snapshot(actuals, forecasts, snapshot_dir=tmp_path)
    assert meta["actuals"]["rows"] == 1
    assert meta["forecasts"]["rows"] == 1
    assert (tmp_path / "actuals.csv.gz").exists()
    assert (tmp_path / "forecasts.csv.gz").exists()
    assert (tmp_path / "meta.json").exists()

    # Calling run_ingest without refresh on this directory should return meta idempotently
    idempotent_meta = run_ingest(refresh=False, target_dir=tmp_path)
    assert idempotent_meta["actuals"]["rows"] == 1
