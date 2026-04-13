"""Todo platform for Recurring Todos."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_OVERDUE, OVERDUE_CHECK_INTERVAL, SIGNAL_STORE_UPDATED
from .model import TaskItem
from .recurrence import calculate_next_due
from .store import RecurringTodosStore


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the todo platform."""
    store: RecurringTodosStore = hass.data[DOMAIN]["store"]
    async_add_entities([RecurringTodosListEntity(store, entry)])


class RecurringTodosListEntity(TodoListEntity):
    """A todo list entity backed by RecurringTodosStore."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, store: RecurringTodosStore, entry: ConfigEntry) -> None:
        self._store = store
        self._entry = entry
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id
        self._unsub_overdue_check: Callable[[], None] | None = None
        self._unsub_store_update: Callable[[], None] | None = None

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return all tasks as TodoItem instances."""
        return [
            TodoItem(
                uid=task.uid,
                summary=task.name,
                description=task.description,
                status=task.status,
                due=task.due_date,
            )
            for task in self._store.get_items(self._entry.entry_id)
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose overdue task information and rrule details as entity attributes."""
        tasks = self._store.get_items(self._entry.entry_id)
        overdue = [t for t in tasks if t.is_overdue]
        return {
            "todo_items": [
                {
                    "uid": t.uid,
                    "summary": t.name,
                    "description": t.description,
                    "status": t.status.value if t.status else None,
                    "due": t.due_date.isoformat() if t.due_date else None,
                    "rrule": t.rrule,
                }
                for t in tasks
            ],
            "overdue_count": len(overdue),
            "overdue_tasks": [
                {
                    "uid": t.uid,
                    "name": t.name,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                }
                for t in overdue
            ],
            "tasks_detail": [
                {
                    "uid": t.uid,
                    "name": t.name,
                    "rrule": t.rrule,
                    "completion_count": len(t.completion_history),
                }
                for t in tasks
            ],
        }

    @callback
    def _handle_store_update(self, entity_id: str) -> None:
        """Handle a store update signal for this entity."""
        if entity_id == self.entity_id:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Start periodic overdue check when entity is added."""
        self._unsub_overdue_check = async_track_time_interval(
            self.hass,
            self._async_check_overdue,
            timedelta(seconds=OVERDUE_CHECK_INTERVAL),
        )
        self._unsub_store_update = async_dispatcher_connect(
            self.hass, SIGNAL_STORE_UPDATED, self._handle_store_update
        )
        await self._async_check_overdue()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel periodic overdue check when entity is removed."""
        if self._unsub_overdue_check is not None:
            self._unsub_overdue_check()
            self._unsub_overdue_check = None
        if self._unsub_store_update is not None:
            self._unsub_store_update()
            self._unsub_store_update = None

    async def _async_check_overdue(self, _now: datetime | None = None) -> None:
        """Check for overdue tasks and fire events."""
        tasks = self._store.get_items(self._entry.entry_id)
        overdue = [t for t in tasks if t.is_overdue]

        if not overdue:
            return

        today = dt_util.now().date()
        self.hass.bus.async_fire(
            EVENT_OVERDUE,
            {
                "entity_id": self.entity_id,
                "entry_id": self._entry.entry_id,
                "overdue_tasks": [
                    {
                        "uid": t.uid,
                        "name": t.name,
                        "due_date": t.due_date.isoformat(),
                        "days_overdue": (today - t.due_date).days,
                    }
                    for t in overdue
                ],
                "overdue_count": len(overdue),
            },
        )
        self.async_write_ha_state()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new task from a TodoItem."""
        task = TaskItem(
            name=item.summary,
            description=item.description,
            status=item.status or TodoItemStatus.NEEDS_ACTION,
            due_date=item.due,
        )
        await self._store.async_add_item(self._entry.entry_id, task)
        self.async_write_ha_state()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an existing task, preserving rrule and history."""
        items = self._store.get_items(self._entry.entry_id)
        existing = next((t for t in items if t.uid == item.uid), None)
        if existing is None:
            raise ValueError(f"Task {item.uid} not found")
        existing.name = item.summary
        existing.description = item.description
        existing.due_date = item.due

        completing = (
            item.status == TodoItemStatus.COMPLETED
            and existing.status != TodoItemStatus.COMPLETED
        )
        if completing and existing.rrule:
            existing.completion_history.append(
                {"completed_at": dt_util.now().isoformat()}
            )
            next_due = calculate_next_due(
                existing.rrule, existing.due_date or dt_util.now().date()
            )
            existing.due_date = next_due
            existing.status = TodoItemStatus.NEEDS_ACTION
        else:
            existing.status = item.status

        await self._store.async_update_item(self._entry.entry_id, existing)
        self.async_write_ha_state()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete tasks by their UIDs."""
        await self._store.async_remove_items(self._entry.entry_id, uids)
        self.async_write_ha_state()
