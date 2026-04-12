"""Tests for the notification engine."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.todo import TodoItemStatus

from custom_components.recurring_todos.model import TaskItem
from custom_components.recurring_todos.notify import NotificationChecker

_DT_UTIL_TARGET = "custom_components.recurring_todos.notify.dt_util"


def _mock_now(d: date) -> datetime:
    """Return a timezone-aware datetime for the given date."""
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


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


def _default_options(lead_time=24, interval=12):
    return {
        "notification_lead_time_hours": lead_time,
        "overdue_reminder_interval_hours": interval,
    }


# --- _should_notify tests ---


def test_should_notify_no_due_date(checker):
    task = _make_task(due_date=None)
    assert checker._should_notify(task, datetime.now(tz=timezone.utc), _default_options()) is False


def test_should_notify_completed_task(checker):
    task = _make_task(
        due_date=date.today(), status=TodoItemStatus.COMPLETED
    )
    assert checker._should_notify(task, datetime.now(tz=timezone.utc), _default_options()) is False


def test_should_notify_future_outside_lead_time(checker):
    future = date.today() + timedelta(days=3)
    task = _make_task(due_date=future)
    assert (
        checker._should_notify(task, datetime.now(tz=timezone.utc), _default_options(lead_time=24))
        is False
    )


def test_should_notify_within_lead_time(checker):
    tomorrow = date.today() + timedelta(days=1)
    task = _make_task(due_date=tomorrow)
    # lead_time=48h means we notify up to 2 days before
    assert (
        checker._should_notify(task, datetime.now(tz=timezone.utc), _default_options(lead_time=48))
        is True
    )


def test_should_notify_overdue(checker):
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    assert checker._should_notify(task, datetime.now(tz=timezone.utc), _default_options()) is True


def test_should_notify_rate_limited(checker):
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    now = datetime.now(tz=timezone.utc)
    checker._last_notified["task-1"] = now - timedelta(hours=6)
    assert (
        checker._should_notify(task, now, _default_options(interval=12)) is False
    )


def test_should_notify_rate_limit_expired(checker):
    yesterday = date.today() - timedelta(days=1)
    task = _make_task(due_date=yesterday)
    now = datetime.now(tz=timezone.utc)
    checker._last_notified["task-1"] = now - timedelta(hours=13)
    assert (
        checker._should_notify(task, now, _default_options(interval=12)) is True
    )


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
