"""Tests for the recurrence engine."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.recurring_todos.recurrence import calculate_next_due, validate_rrule


def test_daily_rrule_returns_next_day():
    result = calculate_next_due("FREQ=DAILY", date(2026, 1, 15))
    assert result == date(2026, 1, 16)


def test_weekly_rrule_byday():
    # 2026-01-05 is a Monday
    result = calculate_next_due("FREQ=WEEKLY;BYDAY=MO", date(2026, 1, 5))
    assert result == date(2026, 1, 12)


def test_monthly_rrule():
    result = calculate_next_due("FREQ=MONTHLY", date(2026, 1, 15))
    assert result == date(2026, 2, 15)


def test_yearly_rrule():
    result = calculate_next_due("FREQ=YEARLY", date(2026, 3, 1))
    assert result == date(2027, 3, 1)


def test_rrule_prefix_stripped():
    result = calculate_next_due("RRULE:FREQ=DAILY", date(2026, 1, 15))
    assert result == date(2026, 1, 16)


def test_rrule_with_interval():
    result = calculate_next_due("FREQ=DAILY;INTERVAL=3", date(2026, 1, 10))
    assert result == date(2026, 1, 13)


def test_rrule_with_count_exhausted():
    # COUNT=1 means only the dtstart occurrence; after() returns None
    result = calculate_next_due("FREQ=DAILY;COUNT=1", date(2026, 1, 10))
    assert result is None


def test_rrule_with_until_exhausted():
    result = calculate_next_due(
        "FREQ=DAILY;UNTIL=20260101T000000", date(2026, 1, 2)
    )
    assert result is None


def test_returns_date_not_datetime():
    result = calculate_next_due("FREQ=DAILY", date(2026, 6, 1))
    assert isinstance(result, date)
    assert type(result).__name__ == "date"


def test_invalid_rrule_raises():
    with pytest.raises(Exception):
        calculate_next_due("NOT_A_VALID_RRULE", date(2026, 1, 1))


def test_validate_rrule_valid():
    validate_rrule("FREQ=DAILY")
    validate_rrule("RRULE:FREQ=WEEKLY;BYDAY=MO")
    validate_rrule("FREQ=MONTHLY;INTERVAL=2")


def test_validate_rrule_invalid():
    with pytest.raises(ValueError, match="Invalid RRULE"):
        validate_rrule("NOT_VALID")


def test_validate_rrule_invalid_with_prefix():
    with pytest.raises(ValueError, match="Invalid RRULE"):
        validate_rrule("RRULE:GARBAGE")
