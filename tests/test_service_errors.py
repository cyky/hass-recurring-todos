"""Tests for service handler error paths."""

from __future__ import annotations

from datetime import date

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.recurring_todos.const import DOMAIN
from custom_components.recurring_todos.model import TaskItem

ENTITY_ID = "todo.test_list"


async def test_complete_task_invalid_uid(hass: HomeAssistant, mock_setup_entry):
    """Test that completing a nonexistent task raises ServiceValidationError."""
    with pytest.raises(ServiceValidationError, match="not found"):
        await hass.services.async_call(
            DOMAIN,
            "complete_task",
            {"entity_id": ENTITY_ID, "task_uid": "nonexistent"},
            blocking=True,
        )


async def test_snooze_task_invalid_uid(hass: HomeAssistant, mock_setup_entry):
    """Test that snoozing a nonexistent task raises ServiceValidationError."""
    with pytest.raises(ServiceValidationError, match="not found"):
        await hass.services.async_call(
            DOMAIN,
            "snooze_task",
            {"entity_id": ENTITY_ID, "task_uid": "nonexistent", "days": 1},
            blocking=True,
        )


async def test_update_task_invalid_uid(hass: HomeAssistant, mock_setup_entry):
    """Test that updating a nonexistent task raises ServiceValidationError."""
    with pytest.raises(ServiceValidationError, match="not found"):
        await hass.services.async_call(
            DOMAIN,
            "update_task",
            {"entity_id": ENTITY_ID, "task_uid": "nonexistent", "name": "X"},
            blocking=True,
        )


async def test_create_task_invalid_due_date(hass: HomeAssistant, mock_setup_entry):
    """Test that creating a task with invalid date raises ServiceValidationError."""
    with pytest.raises(ServiceValidationError, match="Invalid due_date"):
        await hass.services.async_call(
            DOMAIN,
            "create_task",
            {"entity_id": ENTITY_ID, "name": "Bad date", "due_date": "not-a-date"},
            blocking=True,
        )


async def test_update_task_invalid_due_date(hass: HomeAssistant, mock_setup_entry):
    """Test that updating a task with invalid date raises ServiceValidationError."""
    store = hass.data[DOMAIN]["store"]
    task = TaskItem(name="Existing", due_date=date.today())
    await store.async_add_item(mock_setup_entry.entry_id, task)

    with pytest.raises(ServiceValidationError, match="Invalid due_date"):
        await hass.services.async_call(
            DOMAIN,
            "update_task",
            {
                "entity_id": ENTITY_ID,
                "task_uid": task.uid,
                "due_date": "2026-13-45",
            },
            blocking=True,
        )


async def test_create_task_invalid_rrule(hass: HomeAssistant, mock_setup_entry):
    """Test that creating a task with invalid RRULE raises ServiceValidationError."""
    with pytest.raises(ServiceValidationError, match="Invalid RRULE"):
        await hass.services.async_call(
            DOMAIN,
            "create_task",
            {
                "entity_id": ENTITY_ID,
                "name": "Bad rrule",
                "rrule": "NOT_A_VALID_RRULE",
            },
            blocking=True,
        )


async def test_update_task_invalid_rrule(hass: HomeAssistant, mock_setup_entry):
    """Test that updating a task with invalid RRULE raises ServiceValidationError."""
    store = hass.data[DOMAIN]["store"]
    task = TaskItem(name="Existing", due_date=date.today())
    await store.async_add_item(mock_setup_entry.entry_id, task)

    with pytest.raises(ServiceValidationError, match="Invalid RRULE"):
        await hass.services.async_call(
            DOMAIN,
            "update_task",
            {
                "entity_id": ENTITY_ID,
                "task_uid": task.uid,
                "rrule": "GARBAGE",
            },
            blocking=True,
        )


async def test_create_task_empty_rrule_allowed(hass: HomeAssistant, mock_setup_entry):
    """Test that empty/null RRULE is allowed (one-off task)."""
    await hass.services.async_call(
        DOMAIN,
        "create_task",
        {"entity_id": ENTITY_ID, "name": "One-off", "rrule": ""},
        blocking=True,
    )

    store = hass.data[DOMAIN]["store"]
    items = store.get_items(mock_setup_entry.entry_id)
    assert len(items) == 1
    assert items[0].rrule is None


async def test_create_task_empty_due_date_allowed(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that empty/missing due_date is allowed."""
    await hass.services.async_call(
        DOMAIN,
        "create_task",
        {"entity_id": ENTITY_ID, "name": "No date"},
        blocking=True,
    )

    store = hass.data[DOMAIN]["store"]
    items = store.get_items(mock_setup_entry.entry_id)
    assert len(items) == 1
    assert items[0].due_date is None
