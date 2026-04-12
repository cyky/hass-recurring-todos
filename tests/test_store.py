"""Tests for the storage layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.recurring_todos.model import TaskItem
from custom_components.recurring_todos.store import RecurringTodosStore


@pytest.fixture
def store():
    """Create a store with mocked HA storage backend."""
    mock_ha_store = AsyncMock()
    mock_ha_store.async_load = AsyncMock(return_value=None)
    mock_ha_store.async_save = AsyncMock()

    with patch(
        "custom_components.recurring_todos.store.Store",
        return_value=mock_ha_store,
    ):
        s = RecurringTodosStore(MagicMock())

    return s


async def test_load_empty_store(store):
    await store.async_load()
    assert store.get_items("any_entry") == []


async def test_load_existing_data(store):
    task_dict = TaskItem(name="Dishes").to_dict()
    store._store.async_load.return_value = {"entry1": [task_dict]}
    await store.async_load()
    items = store.get_items("entry1")
    assert len(items) == 1
    assert items[0].name == "Dishes"


async def test_get_items_unknown_entry(store):
    await store.async_load()
    assert store.get_items("nonexistent") == []


async def test_add_item_persists(store):
    await store.async_load()
    task = TaskItem(name="Laundry")
    await store.async_add_item("entry1", task)
    assert len(store.get_items("entry1")) == 1
    store._store.async_save.assert_called_once()


async def test_update_item_replaces(store):
    await store.async_load()
    task = TaskItem(name="Original")
    await store.async_add_item("entry1", task)
    store._store.async_save.reset_mock()

    task.name = "Updated"
    await store.async_update_item("entry1", task)
    assert store.get_items("entry1")[0].name == "Updated"
    store._store.async_save.assert_called_once()


async def test_update_item_not_found_raises(store):
    await store.async_load()
    task = TaskItem(name="Ghost")
    with pytest.raises(KeyError):
        await store.async_update_item("entry1", task)


async def test_remove_item(store):
    await store.async_load()
    task = TaskItem(name="Delete me")
    await store.async_add_item("entry1", task)
    store._store.async_save.reset_mock()

    await store.async_remove_item("entry1", task.uid)
    assert store.get_items("entry1") == []
    store._store.async_save.assert_called_once()


async def test_remove_item_nonexistent_uid(store):
    await store.async_load()
    await store.async_add_item("entry1", TaskItem(name="Keep"))
    store._store.async_save.reset_mock()

    await store.async_remove_item("entry1", "no-such-uid")
    assert len(store.get_items("entry1")) == 1


async def test_remove_entry(store):
    await store.async_load()
    await store.async_add_item("entry1", TaskItem(name="T"))
    store._store.async_save.reset_mock()

    await store.async_remove_entry("entry1")
    assert store.get_items("entry1") == []
    store._store.async_save.assert_called_once()


async def test_remove_entry_nonexistent(store):
    await store.async_load()
    await store.async_remove_entry("no-such-entry")
    # No error, no save call for nonexistent entry
    store._store.async_save.assert_not_called()


async def test_save_serializes_correctly(store):
    await store.async_load()
    task = TaskItem(name="Check format")
    await store.async_add_item("entry1", task)

    saved_data = store._store.async_save.call_args[0][0]
    assert "entry1" in saved_data
    assert saved_data["entry1"][0]["name"] == "Check format"
    assert isinstance(saved_data["entry1"][0]["status"], str)
