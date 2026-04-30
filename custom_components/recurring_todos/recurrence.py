"""Recurrence engine using iCal RRULE via python-dateutil."""

from __future__ import annotations

from datetime import date, datetime, timedelta

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


def calculate_previous_due(rrule_string: str, before_date: date) -> date | None:
    """Return the latest occurrence strictly before before_date, or None.

    Used to reconstruct the prior due date when undoing a legacy completion
    that wasn't recorded with due_date_before. The anchor is chosen so that
    before_date itself lands on the rule, which differs by FREQ (weekly needs
    same weekday; monthly/yearly need same day-of-month).
    """
    rule_text = rrule_string.removeprefix("RRULE:")
    upper = rule_text.upper()
    target = datetime(before_date.year, before_date.month, before_date.day)

    if "FREQ=WEEKLY" in upper:
        anchor_dt = target - timedelta(weeks=520)
    elif "FREQ=MONTHLY" in upper or "FREQ=YEARLY" in upper:
        try:
            anchor_d = before_date.replace(year=before_date.year - 10)
        except ValueError:
            anchor_d = before_date.replace(year=before_date.year - 10, day=28)
        anchor_dt = datetime(anchor_d.year, anchor_d.month, anchor_d.day)
    else:
        anchor_dt = target - timedelta(days=365 * 10)

    rule = rrulestr(rule_text, dtstart=anchor_dt)
    prev_dt = rule.before(target)
    if prev_dt is None:
        return None
    return prev_dt.date()
