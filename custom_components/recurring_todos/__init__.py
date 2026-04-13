"""Recurring Todos - Recurring task/chore tracking for Home Assistant."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.todo import TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_COMPLETE_TASK,
    SERVICE_CREATE_TASK,
    SERVICE_SNOOZE_TASK,
    SERVICE_UPDATE_TASK,
    SIGNAL_STORE_UPDATED,
)
from .notify import NotificationChecker
from .recurrence import calculate_next_due
from .model import TaskItem
from .store import RecurringTodosStore

DATA_STORE = "store"
DATA_ENTRY_IDS = "entry_ids"
DATA_NOTIFY_UNSUBS = "notify_unsubs"

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

SERVICE_SCHEMA_CREATE = vol.Schema(
    {
        vol.Required("entity_id"): str,
        vol.Required("name"): str,
        vol.Optional("description"): str,
        vol.Optional("due_date"): str,
        vol.Optional("rrule"): str,
    }
)

SERVICE_SCHEMA_UPDATE = vol.Schema(
    {
        vol.Required("entity_id"): str,
        vol.Required("task_uid"): str,
        vol.Optional("name"): str,
        vol.Optional("description"): str,
        vol.Optional("due_date"): str,
        vol.Optional("rrule"): str,
    }
)

CARD_VERSION = "0.1.0"
CARD_URL = f"/api/{DOMAIN}/recurring-todos-card.js"
CARD_URL_CACHE_BUST = f"{CARD_URL}?v={CARD_VERSION}"
CARD_PATH = Path(__file__).parent / "www" / "recurring-todos-card.js"


def _resolve_store(
    hass: HomeAssistant, entity_id: str
) -> tuple[RecurringTodosStore, str]:
    """Resolve an entity_id to its store and config entry ID."""
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None or entry.config_entry_id is None:
        raise ValueError(f"Entity {entity_id} not found in registry")

    config_entry_id = entry.config_entry_id
    domain_data = hass.data.get(DOMAIN)
    if domain_data is None:
        raise ValueError(f"No store for config entry {config_entry_id}")

    return domain_data[DATA_STORE], config_entry_id


def _async_refresh_entity(hass: HomeAssistant, entity_id: str) -> None:
    """Signal the entity to update its state after a store change."""
    async_dispatcher_send(hass, SIGNAL_STORE_UPDATED, entity_id)


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
            {"completed_at": dt_util.now().isoformat()}
        )
        task.due_date = calculate_next_due(
            task.rrule, task.due_date or dt_util.now().date()
        )
        task.status = TodoItemStatus.NEEDS_ACTION
    else:
        task.status = TodoItemStatus.COMPLETED

    await store.async_update_item(entry_id, task)
    _async_refresh_entity(hass, call.data["entity_id"])


async def _async_handle_snooze_task(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the snooze_task service call."""
    store, entry_id = _resolve_store(hass, call.data["entity_id"])
    task_uid = call.data["task_uid"]

    items = store.get_items(entry_id)
    task = next((t for t in items if t.uid == task_uid), None)
    if task is None:
        raise ValueError(f"Task {task_uid} not found")

    task.due_date = (task.due_date or dt_util.now().date()) + timedelta(
        days=call.data["days"]
    )
    await store.async_update_item(entry_id, task)
    _async_refresh_entity(hass, call.data["entity_id"])


async def _async_handle_create_task(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the create_task service call."""
    store, entry_id = _resolve_store(hass, call.data["entity_id"])

    due_date_str = call.data.get("due_date")
    due_date = date.fromisoformat(due_date_str) if due_date_str else None

    task = TaskItem(
        name=call.data["name"],
        description=call.data.get("description"),
        due_date=due_date,
        rrule=call.data.get("rrule") or None,
    )
    await store.async_add_item(entry_id, task)
    _async_refresh_entity(hass, call.data["entity_id"])


async def _async_handle_update_task(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the update_task service call."""
    store, entry_id = _resolve_store(hass, call.data["entity_id"])
    task_uid = call.data["task_uid"]

    items = store.get_items(entry_id)
    task = next((t for t in items if t.uid == task_uid), None)
    if task is None:
        raise ValueError(f"Task {task_uid} not found")

    if "name" in call.data:
        task.name = call.data["name"]
    if "description" in call.data:
        task.description = call.data["description"]
    if "due_date" in call.data:
        due_str = call.data["due_date"]
        task.due_date = date.fromisoformat(due_str) if due_str else None
    if "rrule" in call.data:
        task.rrule = call.data["rrule"] or None

    await store.async_update_item(entry_id, task)
    _async_refresh_entity(hass, call.data["entity_id"])


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Recurring Todos from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {
        DATA_STORE: None,
        DATA_ENTRY_IDS: set(),
        DATA_NOTIFY_UNSUBS: {},
    })

    if domain_data[DATA_STORE] is None:
        store = RecurringTodosStore(hass)
        await store.async_load()
        domain_data[DATA_STORE] = store

    domain_data[DATA_ENTRY_IDS].add(entry.entry_id)

    if not hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK):

        async def handle_complete(call: ServiceCall) -> None:
            await _async_handle_complete_task(hass, call)

        async def handle_snooze(call: ServiceCall) -> None:
            await _async_handle_snooze_task(hass, call)

        async def handle_create(call: ServiceCall) -> None:
            await _async_handle_create_task(hass, call)

        async def handle_update(call: ServiceCall) -> None:
            await _async_handle_update_task(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_COMPLETE_TASK,
            handle_complete,
            schema=SERVICE_SCHEMA_COMPLETE,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_SNOOZE_TASK,
            handle_snooze,
            schema=SERVICE_SCHEMA_SNOOZE,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_CREATE_TASK,
            handle_create,
            schema=SERVICE_SCHEMA_CREATE,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_TASK,
            handle_update,
            schema=SERVICE_SCHEMA_UPDATE,
        )

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=True)]
        )
        if "frontend" in hass.config.components:
            from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

            add_extra_js_url(hass, CARD_URL_CACHE_BUST)

    checker = NotificationChecker(hass, entry)
    unsub = await checker.start()
    domain_data[DATA_NOTIFY_UNSUBS][entry.entry_id] = unsub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data = hass.data[DOMAIN]

    unsub = domain_data[DATA_NOTIFY_UNSUBS].pop(entry.entry_id, None)
    if unsub is not None:
        unsub()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data[DATA_ENTRY_IDS].discard(entry.entry_id)
        if not domain_data[DATA_ENTRY_IDS]:
            hass.services.async_remove(DOMAIN, SERVICE_COMPLETE_TASK)
            hass.services.async_remove(DOMAIN, SERVICE_SNOOZE_TASK)
            hass.services.async_remove(DOMAIN, SERVICE_CREATE_TASK)
            hass.services.async_remove(DOMAIN, SERVICE_UPDATE_TASK)
            hass.data.pop(DOMAIN)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry and its stored data."""
    domain_data = hass.data.get(DOMAIN)
    if domain_data is not None and domain_data[DATA_STORE] is not None:
        await domain_data[DATA_STORE].async_remove_entry(entry.entry_id)
