"""Integration tests for the todo entity platform."""

from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.todo import (
    TodoItemStatus,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.recurring_todos.const import DOMAIN, EVENT_OVERDUE
from custom_components.recurring_todos.model import TaskItem

ENTITY_ID = "todo.test_list"


async def test_entity_created(hass: HomeAssistant, mock_setup_entry):
    """Test that a todo entity is created from the config entry."""
    entity_id = "todo.test_list"
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
            "entity_id": "todo.test_list",
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
            "entity_id": "todo.test_list",
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
            "entity_id": "todo.test_list",
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


async def test_create_task_service(hass: HomeAssistant, mock_setup_entry):
    """Test creating a task via the create_task service."""
    await hass.services.async_call(
        DOMAIN,
        "create_task",
        {
            "entity_id": ENTITY_ID,
            "name": "New task",
            "description": "A description",
            "due_date": "2026-05-01",
            "rrule": "FREQ=DAILY",
        },
        blocking=True,
    )

    store = hass.data[DOMAIN]["store"]
    items = store.get_items(mock_setup_entry.entry_id)
    assert len(items) == 1
    assert items[0].name == "New task"
    assert items[0].description == "A description"
    assert items[0].due_date == date(2026, 5, 1)
    assert items[0].rrule == "FREQ=DAILY"


async def test_update_task_service(hass: HomeAssistant, mock_setup_entry):
    """Test updating a task via the update_task service."""
    store = hass.data[DOMAIN]["store"]
    task = TaskItem(name="Original", due_date=date.today(), rrule="FREQ=WEEKLY")
    await store.async_add_item(mock_setup_entry.entry_id, task)

    await hass.services.async_call(
        DOMAIN,
        "update_task",
        {
            "entity_id": ENTITY_ID,
            "task_uid": task.uid,
            "name": "Updated",
            "due_date": "2026-06-15",
            "rrule": "FREQ=MONTHLY",
        },
        blocking=True,
    )

    items = store.get_items(mock_setup_entry.entry_id)
    updated = next(t for t in items if t.uid == task.uid)
    assert updated.name == "Updated"
    assert updated.due_date == date(2026, 6, 15)
    assert updated.rrule == "FREQ=MONTHLY"


async def test_entity_state_updates_after_complete(
    hass: HomeAssistant, mock_setup_entry
):
    """Test that entity state attributes reflect changes after completing a task."""
    store = hass.data[DOMAIN]["store"]
    today = date.today()
    task = TaskItem(name="Recurring", due_date=today, rrule="FREQ=WEEKLY")
    await store.async_add_item(mock_setup_entry.entry_id, task)

    await hass.services.async_call(
        DOMAIN,
        "complete_task",
        {"entity_id": ENTITY_ID, "task_uid": task.uid},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    todo_items = state.attributes.get("todo_items", [])
    assert len(todo_items) == 1
    assert todo_items[0]["summary"] == "Recurring"
    assert todo_items[0]["due"] > today.isoformat()
    assert todo_items[0]["status"] == "needs_action"


async def test_todo_items_attribute(hass: HomeAssistant, mock_setup_entry):
    """Test that todo_items attribute exposes correct field names and values."""
    store = hass.data[DOMAIN]["store"]
    task = TaskItem(
        name="Dishes",
        description="Kitchen cleanup",
        due_date=date(2026, 4, 20),
        rrule="FREQ=DAILY",
    )
    await store.async_add_item(mock_setup_entry.entry_id, task)

    # Trigger state write via dispatcher
    await hass.services.async_call(
        DOMAIN,
        "snooze_task",
        {"entity_id": ENTITY_ID, "task_uid": task.uid, "days": 1},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    todo_items = state.attributes["todo_items"]
    assert len(todo_items) == 1

    item = todo_items[0]
    assert item["uid"] == task.uid
    assert item["summary"] == "Dishes"
    assert item["description"] == "Kitchen cleanup"
    assert item["due"] == "2026-04-21"
    assert item["rrule"] == "FREQ=DAILY"
    assert item["status"] == "needs_action"


async def test_entity_state_updates_after_create(
    hass: HomeAssistant, mock_setup_entry
):
    """Test that entity state reflects a newly created task immediately."""
    state_before = hass.states.get(ENTITY_ID)
    assert state_before.attributes.get("todo_items", []) == []

    await hass.services.async_call(
        DOMAIN,
        "create_task",
        {"entity_id": ENTITY_ID, "name": "Fresh task", "due_date": "2026-04-15"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state_after = hass.states.get(ENTITY_ID)
    todo_items = state_after.attributes["todo_items"]
    assert len(todo_items) == 1
    assert todo_items[0]["summary"] == "Fresh task"
