"""Recurring Todos - Recurring task/chore tracking for Home Assistant."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import voluptuous as vol

from homeassistant.components.todo import TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS, SERVICE_COMPLETE_TASK, SERVICE_SNOOZE_TASK
from .recurrence import calculate_next_due
from .store import RecurringTodosStore

SERVICE_SCHEMA_COMPLETE = vol.Schema(
    {
        vol.Required("entity_id"): str,
        vol.Required("task_uid"): str,
    }
)

SERVICE_SCHEMA_SNOOZE = vol.Schema(
    {
        vol.Required("entity_id"): str,
        vol.Required("task_uid"): str,
        vol.Optional("days", default=1): vol.All(int, vol.Range(min=1, max=365)),
    }
)


def _resolve_store(
    hass: HomeAssistant, entity_id: str
) -> tuple[RecurringTodosStore, str]:
    """Resolve an entity_id to its store and config entry ID."""
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None or entry.config_entry_id is None:
        raise ValueError(f"Entity {entity_id} not found in registry")

    config_entry_id = entry.config_entry_id
    store = hass.data.get(DOMAIN, {}).get(config_entry_id)
    if store is None:
        raise ValueError(f"No store for config entry {config_entry_id}")

    return store, config_entry_id


async def _async_handle_complete_task(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the complete_task service call."""
    store, entry_id = _resolve_store(hass, call.data["entity_id"])
    task_uid = call.data["task_uid"]

    items = store.get_items(entry_id)
    task = next((t for t in items if t.uid == task_uid), None)
    if task is None:
        raise ValueError(f"Task {task_uid} not found")

    if task.rrule:
        task.completion_history.append(
            {"completed_at": datetime.now().isoformat()}
        )
        task.due_date = calculate_next_due(
            task.rrule, task.due_date or date.today()
        )
        task.status = TodoItemStatus.NEEDS_ACTION
    else:
        task.status = TodoItemStatus.COMPLETED

    await store.async_update_item(entry_id, task)


async def _async_handle_snooze_task(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the snooze_task service call."""
    store, entry_id = _resolve_store(hass, call.data["entity_id"])
    task_uid = call.data["task_uid"]

    items = store.get_items(entry_id)
    task = next((t for t in items if t.uid == task_uid), None)
    if task is None:
        raise ValueError(f"Task {task_uid} not found")

    task.due_date = (task.due_date or date.today()) + timedelta(
        days=call.data["days"]
    )
    await store.async_update_item(entry_id, task)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Recurring Todos from a config entry."""
    store = RecurringTodosStore(hass)
    await store.async_load()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = store

    if not hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK):
        hass.services.async_register(
            DOMAIN,
            SERVICE_COMPLETE_TASK,
            lambda call: _async_handle_complete_task(hass, call),
            schema=SERVICE_SCHEMA_COMPLETE,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_SNOOZE_TASK,
            lambda call: _async_handle_snooze_task(hass, call),
            schema=SERVICE_SCHEMA_SNOOZE,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_COMPLETE_TASK)
            hass.services.async_remove(DOMAIN, SERVICE_SNOOZE_TASK)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry and its stored data."""
    store = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if store is not None:
        await store.async_remove_entry(entry.entry_id)
