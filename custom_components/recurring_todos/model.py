"""Data model for Recurring Todos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import uuid4

from homeassistant.components.todo import TodoItemStatus
from homeassistant.util import dt as dt_util


@dataclass
class TaskItem:
    """A recurring task item with optional recurrence."""

    name: str
    uid: str = field(default_factory=lambda: str(uuid4()))
    description: str | None = None
    status: TodoItemStatus = TodoItemStatus.NEEDS_ACTION
    due_date: date | None = None
    rrule: str | None = None
    completion_history: list[dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: dt_util.now().isoformat())

    @property
    def is_overdue(self) -> bool:
        """Return True if the task is past due and not completed."""
        if self.due_date is None:
            return False
        return (
            self.due_date < dt_util.now().date()
            and self.status != TodoItemStatus.COMPLETED
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "uid": self.uid,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "rrule": self.rrule,
            "completion_history": self.completion_history,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskItem:
        """Deserialize from storage dict."""
        return cls(
            uid=data["uid"],
            name=data["name"],
            description=data.get("description"),
            status=TodoItemStatus(data["status"]),
            due_date=(
                date.fromisoformat(data["due_date"])
                if data.get("due_date")
                else None
            ),
            rrule=data.get("rrule"),
            completion_history=data.get("completion_history", []),
            created_at=data.get("created_at", dt_util.now().isoformat()),
        )
