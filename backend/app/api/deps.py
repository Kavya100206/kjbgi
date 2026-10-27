"""Dependency injection and strict query parameter validation for Vane API."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status

MIN_DATE = date(2026, 1, 1)
MAX_DATE = date(2026, 1, 31)


def parse_iso_date(d_str: str, param_name: str) -> date:
    """Parse YYYY-MM-DD string into a date object, strictly validating range."""
    try:
        parsed = date.fromisoformat(d_str)
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid format for '{param_name}': expected YYYY-MM-DD, got '{d_str}'",
        ) from err

    if parsed < MIN_DATE or parsed > MAX_DATE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{param_name}' {parsed} is outside January 2026 data window ({MIN_DATE} to {MAX_DATE})",
        )
    return parsed


def validate_date_range(
    from_date_str: str,
    to_date_str: str,
) -> tuple[date, date]:
    """Validate that from_date and to_date are valid ISO dates and from_date <= to_date."""
    d_from = parse_iso_date(from_date_str, "from_date")
    d_to = parse_iso_date(to_date_str, "to_date")

    if d_from > d_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date range: 'from_date' ({d_from}) cannot be after 'to_date' ({d_to})",
        )
    return d_from, d_to


def validate_cutoff_hour(cutoff_hour: int) -> int:
    """Validate that cutoff_hour is an integer between 0 and 23."""
    if cutoff_hour < 0 or cutoff_hour > 23:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid 'cutoff_hour': must be between 0 and 23, got {cutoff_hour}",
        )
    return cutoff_hour


def validate_confidence(confidence: float) -> float:
    """Validate that confidence is between 0.50 and 0.99."""
    if confidence < 0.50 or confidence > 0.99:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid 'confidence': must be between 0.50 and 0.99, got {confidence}",
        )
    return confidence
