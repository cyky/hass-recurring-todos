"""Tests for the notification engine."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.todo import TodoItemStatus

from custom_components.recurring_todos.model import TaskItem
from custom_components.recurring_todos.notify import NotificationChecker

_DT_UTIL_TARGET = "custom_components.recurring_todos.notify.dt_util"


def _mock_now(d: date, hour: int = 0, minute: int = 0) -> datetime:
    """Return a timezone-aware datetime for the given date and optional time."""
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)


@pytest.fixture
def checker():
    """Create a NotificationChecker with mocked hass and entry."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "Family Chores"
    c = NotificationChecker(mock_hass, mock_entry)
    return c


def _make_task(
    name="Test Task",
    due_date=None,
    status=TodoItemStatus.NEEDS_ACTION,
    uid="task-1",
):
    return TaskItem(name=name, uid=uid, due_date=due_date, status=status)


def _default_options(lead_time=24, interval=12, quiet_enabled=True, quiet_start="22:00:00", quiet_end="08:00:00"):
    return {
        "notification_lead_time_hours": lead_time,
        "overdue_reminder_interval_hours": interval,
        "quiet_hours_enabled": quiet_enabled,
        "quiet_hours_start": quiet_start,
        "quiet_hours_end": quiet_end,
    }


# --- _should_notify tests ---


def test_should_notify_no_due_date(checker):
    task = _make_task(due_date=None)
    now = _mock_now(date.today(), hour=10)
    assert checker._should_notify(task, now, _default_options()) is False


def test_should_notify_completed_task(checker):
    task = _make_task(
        due_date=date.today(), status=TodoItemStatus.COMPLETED
    )
    now = _mock_now(date.today(), hour=10)
    assert checker._should_notify(task, now, _default_options()) is False


def test_should_notify_future_outside_lead_time(checker):
    future = date.today() + timedelta(days=3)
    task = _make_task(due_date=future)
    now = _mock_now(date.today(), hour=10)
    assert (
        checker._should_notify(task, now, _default_options(lead_time=24))
        is False
    )


def test_should_notify_within_lead_time(checker):
    tomorrow = date.today() + timedelta(days=1)
    task = _make_task(due_date=tomorrow)
    now = _mock_now(date.today(), hour=10)
    # lead_time=48h means we notify up to 2 days before
    assert (
        checker._should_notify(task, now, _default_options(lead_time=48))
        is True
    )


def test_should_notify_overdue(checker):
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    now = _mock_now(date.today(), hour=10)
    assert checker._should_notify(task, now, _default_options()) is True


def test_should_notify_rate_limited(checker):
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    now = _mock_now(date.today(), hour=10)
    checker._last_notified["task-1"] = now - timedelta(hours=6)
    assert (
        checker._should_notify(task, now, _default_options(interval=12)) is False
    )


def test_should_notify_rate_limit_expired(checker):
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    now = _mock_now(date.today(), hour=10)
    checker._last_notified["task-1"] = now - timedelta(hours=13)
    assert (
        checker._should_notify(task, now, _default_options(interval=12)) is True
    )


# --- quiet hours tests ---


def test_should_notify_during_quiet_hours_overnight(checker):
    """Notifications suppressed during overnight quiet hours (22:00–08:00)."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    # 23:00 is within default quiet hours 22:00–08:00
    now = _mock_now(date.today(), hour=23)
    assert checker._should_notify(task, now, _default_options()) is False


def test_should_notify_during_quiet_hours_early_morning(checker):
    """Notifications suppressed in early morning during overnight quiet hours."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    # 05:00 is within default quiet hours 22:00–08:00
    now = _mock_now(date.today(), hour=5)
    assert checker._should_notify(task, now, _default_options()) is False


def test_should_notify_after_quiet_hours(checker):
    """Notifications fire after quiet hours end."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    # 09:00 is outside default quiet hours 22:00–08:00
    now = _mock_now(date.today(), hour=9)
    assert checker._should_notify(task, now, _default_options()) is True


def test_should_notify_exactly_at_quiet_hours_end(checker):
    """Notifications fire at exactly the quiet hours end time."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    # 08:00 == quiet_end, should notify (end is exclusive)
    now = _mock_now(date.today(), hour=8)
    assert checker._should_notify(task, now, _default_options()) is True


def test_should_notify_exactly_at_quiet_hours_start(checker):
    """Notifications suppressed at exactly the quiet hours start time."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    # 22:00 == quiet_start, should suppress (start is inclusive)
    now = _mock_now(date.today(), hour=22)
    assert checker._should_notify(task, now, _default_options()) is False


def test_should_notify_same_day_quiet_hours(checker):
    """Same-day quiet hours range (e.g. 01:00–06:00) works correctly."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    opts = _default_options(quiet_start="01:00:00", quiet_end="06:00:00")
    # 03:00 is within 01:00–06:00
    assert checker._should_notify(task, _mock_now(date.today(), hour=3), opts) is False
    # 10:00 is outside 01:00–06:00
    assert checker._should_notify(task, _mock_now(date.today(), hour=10), opts) is True
    # 23:00 is outside 01:00–06:00
    assert checker._should_notify(task, _mock_now(date.today(), hour=23), opts) is True


def test_should_notify_custom_quiet_hours(checker):
    """Custom quiet hours range is respected."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    opts = _default_options(quiet_start="20:00:00", quiet_end="10:00:00")
    # 21:00 is within 20:00–10:00
    assert checker._should_notify(task, _mock_now(date.today(), hour=21), opts) is False
    # 07:00 is within 20:00–10:00
    assert checker._should_notify(task, _mock_now(date.today(), hour=7), opts) is False
    # 12:00 is outside 20:00–10:00
    assert checker._should_notify(task, _mock_now(date.today(), hour=12), opts) is True


def test_should_notify_quiet_hours_disabled(checker):
    """Notifications fire during quiet hours when the toggle is off."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    opts = _default_options(quiet_enabled=False)
    # 03:00 would normally be suppressed, but quiet hours are disabled
    now = _mock_now(date.today(), hour=3)
    assert checker._should_notify(task, now, opts) is True


def test_suppressed_during_quiet_hours_fires_after(checker):
    """Notification suppressed at midnight fires on first check after quiet hours."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    opts = _default_options()

    # Suppressed at 00:00 during quiet hours
    assert checker._should_notify(task, _mock_now(date.today(), hour=0), opts) is False
    # Still suppressed at 07:30
    assert checker._should_notify(task, _mock_now(date.today(), hour=7, minute=30), opts) is False
    # Fires at 08:00 when quiet hours end
    assert checker._should_notify(task, _mock_now(date.today(), hour=8), opts) is True
    # No _last_notified was recorded during quiet hours, so nothing blocks it


def test_suppressed_during_quiet_hours_no_stale_rate_limit(checker):
    """Rate limit timer does not tick during quiet hours suppression."""
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    opts = _default_options(interval=12)

    # Suppressed at 23:00 — _last_notified is NOT set
    assert checker._should_notify(task, _mock_now(date.today(), hour=23), opts) is False
    assert task.uid not in checker._last_notified

    # First notification fires at 08:00
    assert checker._should_notify(task, _mock_now(date.today(), hour=8), opts) is True


# --- _build_message tests ---


@patch(_DT_UTIL_TARGET)
def test_build_message_overdue_1_day(mock_dt, checker):
    mock_dt.now.return_value = _mock_now(date(2026, 4, 11))
    task = _make_task(name="Dishes", due_date=date(2026, 4, 10))
    title, msg = checker._build_message(task)
    assert title == "Family Chores"
    assert "1 day" in msg
    assert "overdue" in msg
    assert "days" not in msg  # singular


@patch(_DT_UTIL_TARGET)
def test_build_message_overdue_3_days(mock_dt, checker):
    mock_dt.now.return_value = _mock_now(date(2026, 4, 13))
    task = _make_task(name="Dishes", due_date=date(2026, 4, 10))
    _, msg = checker._build_message(task)
    assert "3 days" in msg
    assert "overdue" in msg


@patch(_DT_UTIL_TARGET)
def test_build_message_due_today(mock_dt, checker):
    mock_dt.now.return_value = _mock_now(date(2026, 4, 10))
    task = _make_task(name="Dishes", due_date=date(2026, 4, 10))
    _, msg = checker._build_message(task)
    assert "due today" in msg


@patch(_DT_UTIL_TARGET)
def test_build_message_due_tomorrow(mock_dt, checker):
    mock_dt.now.return_value = _mock_now(date(2026, 4, 10))
    task = _make_task(name="Dishes", due_date=date(2026, 4, 11))
    _, msg = checker._build_message(task)
    assert "1 day" in msg
    assert "days" not in msg  # singular


@patch(_DT_UTIL_TARGET)
def test_build_message_due_in_3_days(mock_dt, checker):
    mock_dt.now.return_value = _mock_now(date(2026, 4, 10))
    task = _make_task(name="Dishes", due_date=date(2026, 4, 13))
    _, msg = checker._build_message(task)
    assert "3 days" in msg


def test_build_message_no_due_date(checker):
    task = _make_task(name="Random", due_date=None)
    _, msg = checker._build_message(task)
    assert "needs attention" in msg
