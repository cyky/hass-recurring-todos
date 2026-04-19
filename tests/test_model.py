"""Tests for the TaskItem data model."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import patch

from homeassistant.components.todo import TodoItemStatus

from custom_components.recurring_todos.model import TaskItem

_MOCK_TARGET = "custom_components.recurring_todos.model.dt_util"


def _mock_now(d: date) -> datetime:
    """Return a timezone-aware datetime for the given date."""
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def test_taskitem_defaults():
    task = TaskItem(name="Test")
    assert task.name == "Test"
    assert task.uid  # non-empty uuid
    assert task.status == TodoItemStatus.NEEDS_ACTION
    assert task.due_date is None
    assert task.rrule is None
    assert task.description is None
    assert task.completion_history == []


def test_is_overdue_past_due_needs_action():
    with patch(_MOCK_TARGET) as mock_dt:
        mock_dt.now.return_value = _mock_now(date(2026, 4, 10))
        task = TaskItem(name="T", due_date=date(2026, 4, 9))
        assert task.is_overdue is True


def test_is_overdue_past_due_completed():
    with patch(_MOCK_TARGET) as mock_dt:
        mock_dt.now.return_value = _mock_now(date(2026, 4, 10))
        task = TaskItem(
            name="T",
            due_date=date(2026, 4, 9),
            status=TodoItemStatus.COMPLETED,
        )
        assert task.is_overdue is False


def test_is_overdue_today():
    with patch(_MOCK_TARGET) as mock_dt:
        mock_dt.now.return_value = _mock_now(date(2026, 4, 10))
        task = TaskItem(name="T", due_date=date(2026, 4, 10))
        assert task.is_overdue is False


def test_is_overdue_future():
    with patch(_MOCK_TARGET) as mock_dt:
        mock_dt.now.return_value = _mock_now(date(2026, 4, 10))
        task = TaskItem(name="T", due_date=date(2026, 4, 11))
        assert task.is_overdue is False


def test_is_overdue_no_due_date():
    task = TaskItem(name="T")
    assert task.is_overdue is False


def test_to_dict_roundtrip():
    task = TaskItem(
        name="Dishes",
        description="Kitchen sink",
        due_date=date(2026, 5, 1),
        rrule="FREQ=WEEKLY;BYDAY=MO",
        completion_history=[{"completed_at": "2026-04-01T10:00:00"}],
    )
    restored = TaskItem.from_dict(task.to_dict())
    assert restored.uid == task.uid
    assert restored.name == task.name
    assert restored.description == task.description
    assert restored.due_date == task.due_date
    assert restored.rrule == task.rrule
    assert restored.completion_history == task.completion_history
    assert restored.status == task.status


def test_to_dict_with_none_due_date():
    task = TaskItem(name="T")
    d = task.to_dict()
    assert d["due_date"] is None
    restored = TaskItem.from_dict(d)
    assert restored.due_date is None


def test_from_dict_missing_optional_fields():
    d = {
        "uid": "abc",
        "name": "Test",
        "status": "needs_action",
    }
    task = TaskItem.from_dict(d)
    assert task.description is None
    assert task.rrule is None
    assert task.completion_history == []


def test_to_dict_status_is_string():
    task = TaskItem(name="T")
    d = task.to_dict()
    assert isinstance(d["status"], str)
    assert d["status"] == "needs_action"


def test_from_dict_preserves_completion_history():
    history = [
        {"completed_at": "2026-01-01T08:00:00"},
        {"completed_at": "2026-01-08T09:00:00"},
    ]
    d = TaskItem(name="T", completion_history=history).to_dict()
    restored = TaskItem.from_dict(d)
    assert restored.completion_history == history
