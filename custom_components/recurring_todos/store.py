"""Storage layer for Recurring Todos."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .model import TaskItem

type StorageData = dict[str, list[dict[str, Any]]]


class RecurringTodosStore:
    """Manage persistent storage for recurring todo task lists."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[StorageData] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, list[TaskItem]] = {}

    async def async_load(self) -> None:
        """Load all data from disk into memory cache."""
        raw: StorageData | None = await self._store.async_load()
        if raw is None:
            self._data = {}
            return
        self._data = {
            entry_id: [TaskItem.from_dict(item) for item in items]
            for entry_id, items in raw.items()
        }

    async def async_save(self) -> None:
        """Serialize in-memory cache and persist to disk."""
        raw: StorageData = {
            entry_id: [item.to_dict() for item in items]
            for entry_id, items in self._data.items()
        }
        await self._store.async_save(raw)

    def get_items(self, entry_id: str) -> list[TaskItem]:
        """Return all TaskItems for a config entry."""
        return self._data.get(entry_id, [])

    async def async_add_item(self, entry_id: str, item: TaskItem) -> None:
        """Append a TaskItem to the entry's list and save."""
        self._data.setdefault(entry_id, []).append(item)
        await self.async_save()

    async def async_update_item(self, entry_id: str, item: TaskItem) -> None:
        """Replace the TaskItem matching item.uid and save."""
        items = self._data.get(entry_id, [])
        for i, existing in enumerate(items):
            if existing.uid == item.uid:
                items[i] = item
                await self.async_save()
                return
        raise KeyError(f"Task {item.uid} not found in entry {entry_id}")

    async def async_remove_item(self, entry_id: str, uid: str) -> None:
        """Remove a TaskItem by uid and save."""
        if entry_id in self._data:
            self._data[entry_id] = [
                item for item in self._data[entry_id] if item.uid != uid
            ]
            await self.async_save()

    async def async_remove_items(self, entry_id: str, uids: list[str]) -> None:
        """Remove multiple TaskItems by uid in a single save."""
        if entry_id in self._data:
            uid_set = set(uids)
            self._data[entry_id] = [
                item for item in self._data[entry_id] if item.uid not in uid_set
            ]
            await self.async_save()

    async def async_remove_entry(self, entry_id: str) -> None:
        """Remove all data for a config entry and save."""
        if self._data.pop(entry_id, None) is not None:
            await self.async_save()
