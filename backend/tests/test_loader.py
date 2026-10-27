"""Tests for app.data.loader — schema validation, error handling, and caching."""

from __future__ import annotations

import pandas as pd
import pytest

from app.data.loader import (
    clear_loader_cache,
    get_cached_actuals,
    get_cached_forecasts,
    get_cached_meta,
    load_actuals,
    load_forecasts,
    load_meta,
)


def test_load_actuals_committed_snapshot():
    df = load_actuals()
    assert len(df) == 1536
    assert set(df.columns) == {
        "dataset",
        "publishTime",
        "startTime",
        "settlementDate",
        "settlementPeriod",
        "fuelType",
        "generation",
    }
    # Check types
    assert pd.api.types.is_datetime64_any_dtype(df["startTime"])
    assert pd.api.types.is_datetime64_any_dtype(df["publishTime"])
    assert df["startTime"].dt.tz is not None  # timezone-aware UTC
    assert (df["generation"] >= 0).all()
    assert df["fuelType"].unique().tolist() == ["WIND"]


def test_load_forecasts_committed_snapshot():
    df = load_forecasts()
    assert len(df) == 19856
    assert set(df.columns) == {
        "dataset",
        "publishTime",
        "startTime",
        "generation",
        "horizon_h",
    }
    assert pd.api.types.is_datetime64_any_dtype(df["publishTime"])
    assert pd.api.types.is_datetime64_any_dtype(df["startTime"])
    assert df["publishTime"].dt.tz is not None
    assert (df["generation"] >= 0).all()
    # Check horizon computation
    expected_horizon = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600.0
    pd.testing.assert_series_equal(df["horizon_h"], expected_horizon, check_names=False)


def test_load_meta_committed_snapshot():
    meta = load_meta()
    assert "ingested_at" in meta
    assert "window" in meta
    assert meta["actuals"]["rows"] == 1536
    assert meta["forecasts"]["rows"] == 19856
    assert meta["forecasts"]["unique_vintages"] == 272


def test_caching_and_clear():
    clear_loader_cache()
    df1 = get_cached_actuals()
    df2 = get_cached_actuals()
    assert df1 is df2  # identical cached object

    meta1 = get_cached_meta()
    meta2 = get_cached_meta()
    assert meta1 is meta2

    fc1 = get_cached_forecasts()
    fc2 = get_cached_forecasts()
    assert fc1 is fc2

    clear_loader_cache()


def test_loader_fails_loudly_on_missing_file(tmp_path):
    missing_file = tmp_path / "nonexistent.csv.gz"
    with pytest.raises(FileNotFoundError, match="not found"):
        load_actuals(missing_file)

    with pytest.raises(FileNotFoundError, match="not found"):
        load_forecasts(missing_file)

    with pytest.raises(FileNotFoundError, match="not found"):
        load_meta(missing_file)


def test_loader_fails_loudly_on_missing_columns(tmp_path):
    # Missing settlementPeriod
    bad_df = pd.DataFrame(
        [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "fuelType": "WIND",
                "generation": 5000,
            }
        ]
    )
    bad_file = tmp_path / "bad_actuals.csv.gz"
    bad_df.to_csv(bad_file, index=False, compression="gzip")

    with pytest.raises(ValueError, match="missing required columns.*settlementPeriod"):
        load_actuals(bad_file)


def test_loader_fails_loudly_on_empty_dataset(tmp_path):
    empty_df = pd.DataFrame(columns=["dataset", "publishTime", "startTime", "generation"])
    empty_file = tmp_path / "empty_forecasts.csv.gz"
    empty_df.to_csv(empty_file, index=False, compression="gzip")

    with pytest.raises(ValueError, match="dataset is empty"):
        load_forecasts(empty_file)


def test_loader_fails_loudly_on_negative_generation(tmp_path):
    neg_df = pd.DataFrame(
        [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-01T02:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "generation": -100,
            }
        ]
    )
    neg_file = tmp_path / "neg_forecasts.csv.gz"
    neg_df.to_csv(neg_file, index=False, compression="gzip")

    with pytest.raises(ValueError, match="negative generation"):
        load_forecasts(neg_file)


def test_load_meta_fails_loudly_on_corrupt_data(tmp_path):
    bad_meta_file = tmp_path / "meta.json"
    bad_meta_file.write_text('{"some_key": 123}', encoding="utf-8")

    with pytest.raises(ValueError, match="missing required keys"):
        load_meta(bad_meta_file)
