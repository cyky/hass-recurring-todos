"""Integration tests for the todo entity platform."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.recurring_todos.const import DOMAIN, EVENT_OVERDUE
from custom_components.recurring_todos.model import TaskItem


async def test_entity_created(hass: HomeAssistant, mock_setup_entry):
    """Test that a todo entity is created from the config entry."""
    entity_id = f"todo.test_list"
    state = hass.states.get(entity_id)
    assert state is not None


async def test_create_and_retrieve_task(hass: HomeAssistant, mock_setup_entry):
    """Test creating a task via the todo platform."""
    store = hass.data[DOMAIN]["store"]

    task = TaskItem(name="Do dishes", due_date=date.today())
    await store.async_add_item(mock_setup_entry.entry_id, task)

    items = store.get_items(mock_setup_entry.entry_id)
    assert len(items) == 1
    assert items[0].name == "Do dishes"


async def test_complete_recurring_task(hass: HomeAssistant, mock_setup_entry):
    """Test that completing a recurring task advances the due date."""
    store = hass.data[DOMAIN]["store"]
    today = date.today()

    task = TaskItem(
        name="Weekly clean",
        due_date=today,
        rrule="FREQ=WEEKLY",
    )
    await store.async_add_item(mock_setup_entry.entry_id, task)

    # Simulate completion via the complete_task service
    await hass.services.async_call(
        DOMAIN,
        "complete_task",
        {
            "entity_id": f"todo.test_list",
            "task_uid": task.uid,
        },
        blocking=True,
    )

    items = store.get_items(mock_setup_entry.entry_id)
    completed_task = next(t for t in items if t.uid == task.uid)

    assert completed_task.status == TodoItemStatus.NEEDS_ACTION
    assert completed_task.due_date > today
    assert len(completed_task.completion_history) == 1


async def test_complete_oneoff_task(hass: HomeAssistant, mock_setup_entry):
    """Test that completing a one-off task marks it completed."""
    store = hass.data[DOMAIN]["store"]

    task = TaskItem(name="One-off", due_date=date.today(), rrule=None)
    await store.async_add_item(mock_setup_entry.entry_id, task)

    await hass.services.async_call(
        DOMAIN,
        "complete_task",
        {
            "entity_id": f"todo.test_list",
            "task_uid": task.uid,
        },
        blocking=True,
    )

    items = store.get_items(mock_setup_entry.entry_id)
    completed = next(t for t in items if t.uid == task.uid)
    assert completed.status == TodoItemStatus.COMPLETED


async def test_snooze_task(hass: HomeAssistant, mock_setup_entry):
    """Test that snoozing a task pushes the due date forward."""
    store = hass.data[DOMAIN]["store"]
    today = date.today()

    task = TaskItem(name="Snooze me", due_date=today)
    await store.async_add_item(mock_setup_entry.entry_id, task)

    await hass.services.async_call(
        DOMAIN,
        "snooze_task",
        {
            "entity_id": f"todo.test_list",
            "task_uid": task.uid,
            "days": 3,
        },
        blocking=True,
    )

    items = store.get_items(mock_setup_entry.entry_id)
    snoozed = next(t for t in items if t.uid == task.uid)
    assert snoozed.due_date == today + timedelta(days=3)


async def test_delete_task(hass: HomeAssistant, mock_setup_entry):
    """Test deleting a task removes it from the store."""
    store = hass.data[DOMAIN]["store"]

    task = TaskItem(name="Delete me")
    await store.async_add_item(mock_setup_entry.entry_id, task)
    assert len(store.get_items(mock_setup_entry.entry_id)) == 1

    await store.async_remove_item(mock_setup_entry.entry_id, task.uid)
    assert len(store.get_items(mock_setup_entry.entry_id)) == 0


async def test_overdue_event_fires(hass: HomeAssistant, mock_setup_entry):
    """Test that the overdue event fires for overdue tasks."""
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    store = hass.data[DOMAIN]["store"]
    yesterday = dt_util.now().date() - timedelta(days=1)

    task = TaskItem(name="Overdue task", due_date=yesterday)
    await store.async_add_item(mock_setup_entry.entry_id, task)

    events = []
    hass.bus.async_listen(EVENT_OVERDUE, lambda e: events.append(e))

    # Trigger the periodic overdue check by advancing time
    async_fire_time_changed(hass, fire_all=True)
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["overdue_count"] == 1
    assert events[0].data["overdue_tasks"][0]["name"] == "Overdue task"
