"""Tests for app.domain.pairing — Assumption A7 hourly pairing rule."""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from app.domain.pairing import compute_hourly_actuals, pair_forecast_and_actual

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def test_both_halves_present_correct_mean():
    # 10:00 = 8000 MW, 10:30 = 9000 MW -> mean = 8500 MW
    data = pd.DataFrame(
        [
            {
                "startTime": "2026-01-15T10:00:00Z",
                "generation": 8000,
            },
            {
                "startTime": "2026-01-15T10:30:00Z",
                "generation": 9000,
            },
        ]
    )
    hourly = compute_hourly_actuals(data)
    assert len(hourly) == 1
    row = hourly.iloc[0]
    assert row["startTime"] == datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    assert row["actual_mw"] == 8500.0
    assert bool(row["is_complete"]) is True
    assert row["h00_mw"] == 8000
    assert row["h30_mw"] == 9000


def test_one_half_missing_excluded():
    # Only :00 present, :30 missing -> excluded (is_complete=False, actual_mw=NaN)
    data1 = pd.DataFrame(
        [
            {
                "startTime": "2026-01-15T10:00:00Z",
                "generation": 8000,
            }
        ]
    )
    hourly1 = compute_hourly_actuals(data1)
    assert len(hourly1) == 1
    assert bool(hourly1.iloc[0]["is_complete"]) is False
    assert np.isnan(hourly1.iloc[0]["actual_mw"])

    # Only :30 present, :00 missing -> excluded
    data2 = pd.DataFrame(
        [
            {
                "startTime": "2026-01-15T10:30:00Z",
                "generation": 9000,
            }
        ]
    )
    hourly2 = compute_hourly_actuals(data2)
    assert len(hourly2) == 1
    assert bool(hourly2.iloc[0]["is_complete"]) is False
    assert np.isnan(hourly2.iloc[0]["actual_mw"])


def test_both_halves_missing_excluded():
    data = pd.DataFrame(
        [
            {
                "startTime": "2026-01-15T10:00:00Z",
                "generation": 8000,
            },
            {
                "startTime": "2026-01-15T10:30:00Z",
                "generation": 9000,
            },
            # 11:00 is completely absent
            {
                "startTime": "2026-01-15T12:00:00Z",
                "generation": 7000,
            },
            {
                "startTime": "2026-01-15T12:30:00Z",
                "generation": 7500,
            },
        ]
    )
    hourly = compute_hourly_actuals(data)
    hours = hourly["startTime"].dt.hour.tolist()
    assert 10 in hours
    assert 11 not in hours  # not even generated if no data at all
    assert 12 in hours


def test_boundary_hours_00_and_23():
    data = pd.DataFrame(
        [
            {"startTime": "2026-01-15T00:00:00Z", "generation": 5000},
            {"startTime": "2026-01-15T00:30:00Z", "generation": 5200},
            {"startTime": "2026-01-15T23:00:00Z", "generation": 6000},
            {"startTime": "2026-01-15T23:30:00Z", "generation": 6400},
        ]
    )
    hourly = compute_hourly_actuals(data)
    assert len(hourly) == 2
    row_00 = hourly[hourly["startTime"].dt.hour == 0].iloc[0]
    row_23 = hourly[hourly["startTime"].dt.hour == 23].iloc[0]

    assert row_00["actual_mw"] == 5100.0
    assert bool(row_00["is_complete"]) is True

    assert row_23["actual_mw"] == 6200.0
    assert bool(row_23["is_complete"]) is True


def test_24_rows_per_delivery_day_with_fixture():
    fixture_path = FIXTURES_DIR / "fuelhh_jan15_sample.json"
    assert fixture_path.exists()
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    hourly = compute_hourly_actuals(df)

    assert len(hourly) == 24
    assert hourly["is_complete"].all()
    # Check that hours cover 00:00 to 23:00 in order
    assert hourly["startTime"].dt.hour.tolist() == list(range(24))
    assert (hourly["actual_mw"] > 0).all()


def test_pair_forecast_and_actual_sign_convention():
    fc = pd.DataFrame(
        [
            {"startTime": "2026-01-15T10:00:00Z", "generation": 10000},  # over-forecast
            {"startTime": "2026-01-15T11:00:00Z", "generation": 6000},  # under-forecast
            {"startTime": "2026-01-15T12:00:00Z", "generation": 5000},  # missing actual
        ]
    )
    act = pd.DataFrame(
        [
            {"startTime": "2026-01-15T10:00:00Z", "generation": 8000},
            {"startTime": "2026-01-15T10:30:00Z", "generation": 8000},  # mean = 8000
            {"startTime": "2026-01-15T11:00:00Z", "generation": 7000},
            {"startTime": "2026-01-15T11:30:00Z", "generation": 7000},  # mean = 7000
            # 12:00 missing :30
            {"startTime": "2026-01-15T12:00:00Z", "generation": 5000},
        ]
    )
    paired = pair_forecast_and_actual(fc, act)
    assert len(paired) == 3

    # Row 0: over-forecast: 10000 - 8000 = +2000 MW
    r0 = paired.iloc[0]
    assert bool(r0["is_paired"]) is True
    assert r0["error_mw"] == 2000.0

    # Row 1: under-forecast: 6000 - 7000 = -1000 MW
    r1 = paired.iloc[1]
    assert bool(r1["is_paired"]) is True
    assert r1["error_mw"] == -1000.0

    # Row 2: incomplete actual -> not paired
    r2 = paired.iloc[2]
    assert bool(r2["is_paired"]) is False
    assert np.isnan(r2["error_mw"])
