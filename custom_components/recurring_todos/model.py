"""Data model for Recurring Todos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import uuid4

from homeassistant.components.todo import TodoItemStatus


@dataclass
class TaskItem:
    """A family task item with optional recurrence."""

    name: str
    uid: str = field(default_factory=lambda: str(uuid4()))
    description: str | None = None
    status: TodoItemStatus = TodoItemStatus.NEEDS_ACTION
    due_date: date | None = None
    rrule: str | None = None
    completion_history: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
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
    def from_dict(cls, data: dict) -> TaskItem:
        """Deserialize from storage dict."""
        return cls(
            uid=data["uid"],
            name=data["name"],
            description=data.get("description"),
            status=TodoItemStatus(data["status"]),
            due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            rrule=data.get("rrule"),
            completion_history=data.get("completion_history", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )
