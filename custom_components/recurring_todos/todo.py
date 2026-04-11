"""Todo platform for Recurring Todos."""

from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .model import TaskItem
from .store import RecurringTodosStore


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the todo platform."""
    store: RecurringTodosStore = hass.data[DOMAIN][entry.entry_id]
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

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new task from a TodoItem."""
        task = TaskItem(
            name=item.summary,
            description=item.description,
            status=item.status or TodoItemStatus.NEEDS_ACTION,
            due_date=item.due,
        )
        await self._store.async_add_item(self._entry.entry_id, task)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an existing task, preserving rrule and history."""
        items = self._store.get_items(self._entry.entry_id)
        existing = next((t for t in items if t.uid == item.uid), None)
        if existing is None:
            raise ValueError(f"Task {item.uid} not found")
        existing.name = item.summary
        existing.status = item.status
        existing.description = item.description
        existing.due_date = item.due
        await self._store.async_update_item(self._entry.entry_id, existing)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete tasks by their UIDs."""
        for uid in uids:
            await self._store.async_remove_item(self._entry.entry_id, uid)
