"""Tests for integration setup and teardown."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.recurring_todos.__init__ import (
    CARD_PATH,
    CARD_URL,
    CARD_URL_CACHE_BUST,
    _remove_lovelace_resource,
    _sync_lovelace_resource,
)
from custom_components.recurring_todos.const import (
    DOMAIN,
    SERVICE_COMPLETE_TASK,
    SERVICE_CREATE_TASK,
    SERVICE_SNOOZE_TASK,
    SERVICE_UPDATE_TASK,
)


async def test_setup_entry_loads(hass: HomeAssistant, mock_setup_entry):
    """Test that async_setup_entry loads successfully."""
    assert mock_setup_entry.state is config_entries.ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert mock_setup_entry.entry_id in hass.data[DOMAIN]["entry_ids"]
    assert hass.data[DOMAIN]["store"] is not None


async def test_unload_entry(hass: HomeAssistant, mock_setup_entry):
    """Test that async_unload_entry cleans up."""
    assert await hass.config_entries.async_unload(mock_setup_entry.entry_id)
    assert mock_setup_entry.state is config_entries.ConfigEntryState.NOT_LOADED


async def test_all_services_registered(hass: HomeAssistant, mock_setup_entry):
    """Test that all four custom services are registered after setup."""
    assert hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK)
    assert hass.services.has_service(DOMAIN, SERVICE_SNOOZE_TASK)
    assert hass.services.has_service(DOMAIN, SERVICE_CREATE_TASK)
    assert hass.services.has_service(DOMAIN, SERVICE_UPDATE_TASK)


async def test_all_services_removed_on_last_unload(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that all services are removed when the last entry is unloaded."""
    await hass.config_entries.async_unload(mock_setup_entry.entry_id)
    assert not hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK)
    assert not hass.services.has_service(DOMAIN, SERVICE_SNOOZE_TASK)
    assert not hass.services.has_service(DOMAIN, SERVICE_CREATE_TASK)
    assert not hass.services.has_service(DOMAIN, SERVICE_UPDATE_TASK)


async def test_notification_checker_unsub_stored(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that notification checker unsub is stored in hass.data."""
    notify_unsubs = hass.data[DOMAIN]["notify_unsubs"]
    assert mock_setup_entry.entry_id in notify_unsubs
    assert callable(notify_unsubs[mock_setup_entry.entry_id])


async def test_card_js_file_exists():
    """Test that the card JS file exists at the expected path."""
    assert CARD_PATH.is_file(), f"Card JS missing: {CARD_PATH}"


async def test_card_js_has_custom_cards_registration():
    """Test that the card JS registers itself in window.customCards."""
    content = CARD_PATH.read_text()
    assert "window.customCards" in content, "Card JS missing window.customCards registration"
    assert "recurring-todos-card" in content, "Card JS missing card type declaration"


async def test_manifest_has_frontend_hard_dependency():
    """frontend must be a hard dependency so Lovelace is ready when async_setup runs."""
    manifest_path = Path(__file__).parent.parent / "custom_components" / "recurring_todos" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert "frontend" in manifest.get("dependencies", []), (
        "frontend must be in 'dependencies', not 'after_dependencies', "
        "so Lovelace data is available when the integration sets up."
    )
    assert "frontend" not in manifest.get("after_dependencies", [])


async def test_async_setup_registers_lovelace_resource(hass: HomeAssistant):
    """async_setup must register the card as a Lovelace resource."""
    from unittest.mock import AsyncMock, MagicMock

    from custom_components.recurring_todos import async_setup

    col = _make_resource_col()
    _patch_lovelace(hass, col)

    http_mock = MagicMock()
    http_mock.async_register_static_paths = AsyncMock()
    hass.http = http_mock

    result = await async_setup(hass, {})

    assert result is True
    col.async_create_item.assert_awaited_once_with(
        {"res_type": "module", "url": CARD_URL_CACHE_BUST}
    )


async def test_async_setup_does_not_use_add_extra_js_url(hass: HomeAssistant):
    """Card must not be registered via add_extra_js_url."""
    col = _make_resource_col()
    _patch_lovelace(hass, col)

    http_mock = MagicMock()
    http_mock.async_register_static_paths = AsyncMock()
    hass.http = http_mock

    hass.data["frontend_extra_module_url"] = set()

    from custom_components.recurring_todos import async_setup
    await async_setup(hass, {})

    assert hass.data["frontend_extra_module_url"] == set()


async def test_card_url_uses_manifest_version(hass: HomeAssistant):
    """Cache-bust query string must track manifest.json version."""
    manifest_path = Path(__file__).parent.parent / "custom_components" / "recurring_todos" / "manifest.json"
    manifest_version = json.loads(manifest_path.read_text())["version"]

    assert CARD_URL_CACHE_BUST.endswith(f"?v={manifest_version}"), (
        f"Cache-bust URL {CARD_URL_CACHE_BUST!r} must end with the manifest "
        f"version ?v={manifest_version}"
    )


# --- Multi-entry edge cases ---


def _make_entry(unique_id: str, title: str = "List") -> MockConfigEntry:
    """Helper to create a config entry with a unique ID."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={"name": title},
        options={},
        unique_id=unique_id,
        version=1,
    )


async def _setup_two_entries(hass: HomeAssistant):
    """Set up two config entries sequentially and return them."""
    entry1 = _make_entry("entry_1", "List A")
    entry1.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    entry2 = _make_entry("entry_2", "List B")
    entry2.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    return entry1, entry2


async def test_two_entries_share_single_store(hass: HomeAssistant):
    """Test that multiple config entries share the same store instance."""
    entry1, entry2 = await _setup_two_entries(hass)

    domain_data = hass.data[DOMAIN]
    assert domain_data["store"] is not None
    assert entry1.entry_id in domain_data["entry_ids"]
    assert entry2.entry_id in domain_data["entry_ids"]


async def test_services_persist_after_partial_unload(hass: HomeAssistant):
    """Test that services remain when one of two entries is unloaded."""
    entry1, entry2 = await _setup_two_entries(hass)

    # Unload first entry — services should stay
    assert await hass.config_entries.async_unload(entry1.entry_id)
    assert hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK)
    assert hass.services.has_service(DOMAIN, SERVICE_SNOOZE_TASK)
    assert DOMAIN in hass.data

    # Unload second entry — services should be gone
    assert await hass.config_entries.async_unload(entry2.entry_id)
    assert not hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK)
    assert DOMAIN not in hass.data


async def test_domain_data_cleaned_up_on_last_unload(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that hass.data[DOMAIN] is removed when the last entry unloads."""
    assert DOMAIN in hass.data
    await hass.config_entries.async_unload(mock_setup_entry.entry_id)
    assert DOMAIN not in hass.data


async def test_reload_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test that unloading and re-setting up an entry works cleanly."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is config_entries.ConfigEntryState.NOT_LOADED

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is config_entries.ConfigEntryState.LOADED
    assert hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK)


async def test_notify_unsub_called_on_unload(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that the notification checker unsubscribe is actually called on unload."""
    from unittest.mock import MagicMock

    mock_unsub = MagicMock()
    hass.data[DOMAIN]["notify_unsubs"][mock_setup_entry.entry_id] = mock_unsub
    await hass.config_entries.async_unload(mock_setup_entry.entry_id)
    mock_unsub.assert_called_once()


async def test_notify_unsub_removed_on_unload(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that notify unsub entry is removed from dict after unload."""
    entry_id = mock_setup_entry.entry_id
    assert entry_id in hass.data[DOMAIN]["notify_unsubs"]
    await hass.config_entries.async_unload(entry_id)
    # Domain data is cleared on last unload, so just verify it didn't raise
    assert DOMAIN not in hass.data


async def test_card_resource_registered_once_with_multiple_entries(hass: HomeAssistant):
    """Lovelace resource is registered exactly once across multiple config entries."""
    col = _make_resource_col()
    _patch_lovelace(hass, col)

    entry1 = _make_entry("entry_1", "List A")
    entry1.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    entry2 = _make_entry("entry_2", "List B")
    entry2.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    assert col.async_create_item.await_count == 1, (
        f"Resource should be registered once, got {col.async_create_item.await_count}"
    )


async def test_unload_entry_with_missing_domain_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry,
):
    """Test that async_unload_entry handles missing domain data gracefully."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Simulate domain data already cleaned up (e.g. double unload)
    hass.data.pop(DOMAIN, None)

    # Should return True without raising
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)


# --- Lovelace resource registration ---


def _make_resource_col(items: list[dict] | None = None):
    """Build a minimal ResourceStorageCollection mock."""
    from homeassistant.components.lovelace.resources import ResourceStorageCollection

    col = MagicMock(spec=ResourceStorageCollection)
    col.loaded = True
    col.data = {item["id"]: item for item in (items or [])}
    col.async_create_item = AsyncMock(side_effect=lambda d: col.data.update(
        {f"new_{len(col.data)}": {"id": f"new_{len(col.data)}", "url": d["url"], "type": "module"}}
    ))
    col.async_delete_item = AsyncMock(side_effect=lambda item_id: col.data.pop(item_id, None))
    return col


def _patch_lovelace(hass, resource_col):
    """Inject a mock LovelaceData into hass.data."""
    from homeassistant.components.lovelace import LOVELACE_DATA

    lovelace_data = MagicMock()
    lovelace_data.resources = resource_col
    hass.data[LOVELACE_DATA] = lovelace_data


async def test_sync_lovelace_resource_registers_card(hass: HomeAssistant):
    """Resource is created when not yet registered."""
    col = _make_resource_col()
    _patch_lovelace(hass, col)

    await _sync_lovelace_resource(hass)

    col.async_create_item.assert_awaited_once_with(
        {"res_type": "module", "url": CARD_URL_CACHE_BUST}
    )


async def test_sync_lovelace_resource_skips_if_current(hass: HomeAssistant):
    """No write when current version is already registered."""
    col = _make_resource_col([{"id": "abc", "url": CARD_URL_CACHE_BUST, "type": "module"}])
    _patch_lovelace(hass, col)

    await _sync_lovelace_resource(hass)

    col.async_create_item.assert_not_awaited()
    col.async_delete_item.assert_not_awaited()


async def test_sync_lovelace_resource_replaces_stale_version(hass: HomeAssistant):
    """Stale version is removed and current version is added."""
    stale_url = f"{CARD_URL}?v=0.1.0"
    col = _make_resource_col([{"id": "old", "url": stale_url, "type": "module"}])
    _patch_lovelace(hass, col)

    await _sync_lovelace_resource(hass)

    col.async_delete_item.assert_awaited_once_with("old")
    col.async_create_item.assert_awaited_once()


async def test_sync_lovelace_resource_no_lovelace(hass: HomeAssistant):
    """No error when Lovelace is not set up."""
    from homeassistant.components.lovelace import LOVELACE_DATA
    hass.data.pop(LOVELACE_DATA, None)

    # Should not raise
    await _sync_lovelace_resource(hass)


async def test_sync_lovelace_resource_yaml_mode(hass: HomeAssistant):
    """No-op when Lovelace uses YAML resources (read-only)."""
    from homeassistant.components.lovelace import LOVELACE_DATA
    from homeassistant.components.lovelace.resources import ResourceYAMLCollection

    lovelace_data = MagicMock()
    lovelace_data.resources = MagicMock(spec=ResourceYAMLCollection)
    hass.data[LOVELACE_DATA] = lovelace_data

    # Should not raise or write anything
    await _sync_lovelace_resource(hass)


async def test_remove_lovelace_resource(hass: HomeAssistant):
    """Resource is removed when entry is deleted."""
    col = _make_resource_col([{"id": "r1", "url": CARD_URL_CACHE_BUST, "type": "module"}])
    _patch_lovelace(hass, col)

    await _remove_lovelace_resource(hass)

    col.async_delete_item.assert_awaited_once_with("r1")


async def test_remove_lovelace_resource_called_on_last_entry_removal(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
):
    """Lovelace resource is removed when the last config entry is removed."""
    col = _make_resource_col()
    _patch_lovelace(hass, col)

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Seed the collection so there's something to remove
    col.data["r1"] = {"id": "r1", "url": CARD_URL_CACHE_BUST, "type": "module"}

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    col.async_delete_item.assert_awaited_with("r1")


async def test_remove_entry_cleans_stored_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry,
):
    """Test that async_remove_entry cleans up persisted task data."""
    from custom_components.recurring_todos.model import TaskItem
    from custom_components.recurring_todos.store import RecurringTodosStore

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    store = hass.data[DOMAIN]["store"]
    task = TaskItem(name="test task")
    await store.async_add_item(mock_config_entry.entry_id, task)
    assert len(store.get_items(mock_config_entry.entry_id)) == 1

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.config_entries.async_remove(mock_config_entry.entry_id)

    # Verify persisted data is cleaned up by loading a fresh store
    verify_store = RecurringTodosStore(hass)
    await verify_store.async_load()
    assert len(verify_store.get_items(mock_config_entry.entry_id)) == 0
