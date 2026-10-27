"""Tests for app.domain.vintage — Assumption A2 vintage selection at decision cutoff."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd

from app.data.loader import load_forecasts
from app.domain.vintage import (
    get_cutoff_for_target,
    get_vintage_revisions_for_target,
    select_forecasts_at_cutoff,
)


def test_get_cutoff_for_target():
    # Target on 2026-01-15 at 14:00 UTC -> Cutoff is 2026-01-14 at 09:00 UTC
    target = datetime(2026, 1, 15, 14, 0, 0, tzinfo=UTC)
    cutoff = get_cutoff_for_target(target, cutoff_hour=9)
    assert cutoff == datetime(2026, 1, 14, 9, 0, 0, tzinfo=UTC)

    # Boundary hour: 00:00 on 2026-01-15 -> Cutoff is 2026-01-14 at 09:00 UTC
    target_00 = datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC)
    cutoff_00 = get_cutoff_for_target(target_00, cutoff_hour=9)
    assert cutoff_00 == datetime(2026, 1, 14, 9, 0, 0, tzinfo=UTC)


def test_exact_equal_cutoff():
    # Vintage published exactly at cutoff (2026-01-14T09:00:00Z) is eligible
    target_time = "2026-01-15T12:00:00Z"
    df = pd.DataFrame(
        [
            {
                "startTime": target_time,
                "publishTime": "2026-01-14T09:00:00Z",  # exact equal
                "generation": 8500,
            },
            {
                "startTime": target_time,
                "publishTime": "2026-01-14T09:00:01Z",  # 1s after cutoff
                "generation": 9000,
            },
        ]
    )
    selected = select_forecasts_at_cutoff(df, cutoff_hour=9)
    assert len(selected) == 1
    row = selected.iloc[0]
    assert row["forecast_mw"] == 8500
    assert row["publishTime"] == datetime(2026, 1, 14, 9, 0, 0, tzinfo=UTC)
    assert row["forecast_age_h"] == 0.0


def test_none_before_cutoff():
    # Only vintages published AFTER cutoff -> excluded from selected
    target_time = "2026-01-15T12:00:00Z"
    df = pd.DataFrame(
        [
            {
                "startTime": target_time,
                "publishTime": "2026-01-14T09:30:00Z",
                "generation": 9000,
            },
            {
                "startTime": target_time,
                "publishTime": "2026-01-14T11:30:00Z",
                "generation": 9200,
            },
        ]
    )
    selected = select_forecasts_at_cutoff(df, cutoff_hour=9)
    assert selected.empty


def test_multiple_vintages_selects_latest_before_cutoff():
    target_time = "2026-01-15T12:00:00Z"
    df = pd.DataFrame(
        [
            {"startTime": target_time, "publishTime": "2026-01-14T02:30:00Z", "generation": 7000},
            {"startTime": target_time, "publishTime": "2026-01-14T04:30:00Z", "generation": 7500},
            {"startTime": target_time, "publishTime": "2026-01-14T07:30:00Z", "generation": 8000},
            {
                "startTime": target_time,
                "publishTime": "2026-01-14T09:30:00Z",
                "generation": 8500,
            },  # after cutoff
        ]
    )
    selected = select_forecasts_at_cutoff(df, cutoff_hour=9)
    assert len(selected) == 1
    row = selected.iloc[0]
    # Latest before 09:00 is 07:30
    assert row["publishTime"] == datetime(2026, 1, 14, 7, 30, 0, tzinfo=UTC)
    assert row["forecast_mw"] == 8000
    assert row["forecast_age_h"] == 1.5  # 09:00 - 07:30 = 1.5 hours
    # Lead time = 2026-01-15T12:00 - 2026-01-14T07:30 = 28.5 hours
    assert row["horizon_h"] == 28.5


def test_day_boundary():
    # Target 00:00 on Day D vs 23:00 on Day D-1
    df = pd.DataFrame(
        [
            # Delivery Day 2026-01-15 00:00 -> cutoff is 2026-01-14 09:00
            {
                "startTime": "2026-01-15T00:00:00Z",
                "publishTime": "2026-01-14T07:30:00Z",
                "generation": 5000,
            },
            {
                "startTime": "2026-01-15T00:00:00Z",
                "publishTime": "2026-01-14T09:30:00Z",
                "generation": 5500,
            },
            # Delivery Day 2026-01-14 23:00 -> cutoff is 2026-01-13 09:00
            {
                "startTime": "2026-01-14T23:00:00Z",
                "publishTime": "2026-01-13T07:30:00Z",
                "generation": 4000,
            },
            {
                "startTime": "2026-01-14T23:00:00Z",
                "publishTime": "2026-01-13T11:30:00Z",
                "generation": 4500,
            },
        ]
    )
    selected = select_forecasts_at_cutoff(df, cutoff_hour=9)
    assert len(selected) == 2

    row_15 = selected[selected["startTime"] == datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC)].iloc[0]
    assert row_15["publishTime"] == datetime(2026, 1, 14, 7, 30, 0, tzinfo=UTC)

    row_14 = selected[selected["startTime"] == datetime(2026, 1, 14, 23, 0, 0, tzinfo=UTC)].iloc[0]
    assert row_14["publishTime"] == datetime(2026, 1, 13, 7, 30, 0, tzinfo=UTC)


def test_cutoff_hour_change():
    target_time = "2026-01-15T12:00:00Z"
    df = pd.DataFrame(
        [
            {"startTime": target_time, "publishTime": "2026-01-14T04:30:00Z", "generation": 7000},
            {"startTime": target_time, "publishTime": "2026-01-14T07:30:00Z", "generation": 8000},
        ]
    )
    # At cutoff 06:00 -> latest before 06:00 is 04:30
    s_06 = select_forecasts_at_cutoff(df, cutoff_hour=6)
    assert s_06.iloc[0]["publishTime"] == datetime(2026, 1, 14, 4, 30, 0, tzinfo=UTC)
    assert s_06.iloc[0]["forecast_mw"] == 7000

    # At cutoff 09:00 -> latest before 09:00 is 07:30
    s_09 = select_forecasts_at_cutoff(df, cutoff_hour=9)
    assert s_09.iloc[0]["publishTime"] == datetime(2026, 1, 14, 7, 30, 0, tzinfo=UTC)
    assert s_09.iloc[0]["forecast_mw"] == 8000


def test_acceptance_criterion_3_jan_15():
    """AC-3: For delivery day 2026-01-15 at cutoff 09:00, the app shows 24 hourly

    forecast points, each using a forecast published <= 2026-01-14 09:00Z.
    """
    forecasts = load_forecasts()
    selected = select_forecasts_at_cutoff(
        forecasts,
        cutoff_hour=9,
        delivery_date=date(2026, 1, 15),
    )

    assert len(selected) == 24
    cutoff_limit = datetime(2026, 1, 14, 9, 0, 0, tzinfo=UTC)
    assert (selected["publishTime"] <= cutoff_limit).all()
    # All 24 hours 00..23 present
    assert selected["startTime"].dt.hour.tolist() == list(range(24))
    # All 24 hours use the 07:30 vintage
    assert (selected["publishTime"] == datetime(2026, 1, 14, 7, 30, 0, tzinfo=UTC)).all()
    assert (selected["forecast_age_h"] == 1.5).all()


def test_get_vintage_revisions_for_target():
    forecasts = load_forecasts()
    target = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    revisions = get_vintage_revisions_for_target(forecasts, target)

    # Should have multiple vintages published across time for this target
    assert len(revisions) >= 8
    # Should be sorted chronologically by publishTime
    assert revisions["publishTime"].is_monotonic_increasing
