"""Recurrence engine using iCal RRULE via python-dateutil."""

from __future__ import annotations

from datetime import date, datetime

from dateutil.rrule import rrulestr


def validate_rrule(rrule_string: str) -> None:
    """Validate an RRULE string, raising ValueError if invalid."""
    rule_text = rrule_string.removeprefix("RRULE:")
    try:
        rrulestr(rule_text, dtstart=datetime(2000, 1, 1))
    except (ValueError, TypeError) as err:
        raise ValueError(f"Invalid RRULE: {rrule_string!r}: {err}") from err


def calculate_next_due(rrule_string: str, after_date: date) -> date | None:
    """Return the next occurrence after after_date, or None if exhausted.

    Accepts RRULE strings with or without the 'RRULE:' prefix.
    """
    rule_text = rrule_string.removeprefix("RRULE:")
    dtstart = datetime(after_date.year, after_date.month, after_date.day)
    rule = rrulestr(rule_text, dtstart=dtstart)
    next_dt = rule.after(dtstart)
    if next_dt is None:
        return None
    return next_dt.date()
