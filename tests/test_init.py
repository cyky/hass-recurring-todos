"""Tests for integration setup and teardown."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.recurring_todos.const import (
    DOMAIN,
    SERVICE_COMPLETE_TASK,
    SERVICE_CREATE_TASK,
    SERVICE_SNOOZE_TASK,
    SERVICE_UPDATE_TASK,
)
from custom_components.recurring_todos.__init__ import CARD_PATH, CARD_URL_CACHE_BUST


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


async def test_card_js_registered_as_frontend_module(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry,
):
    """Test that the card JS is registered via add_extra_js_url after setup."""
    # Simulate frontend being loaded (initializes the data key that add_extra_js_url needs)
    hass.data["frontend_extra_module_url"] = set()
    hass.config.components.add("frontend")

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    extra_urls = hass.data["frontend_extra_module_url"]
    assert CARD_URL_CACHE_BUST in extra_urls, (
        f"Card URL {CARD_URL_CACHE_BUST} not in frontend modules: {extra_urls}"
    )


async def test_card_js_not_registered_without_frontend(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that setup succeeds even when frontend is not loaded."""
    assert mock_setup_entry.state is config_entries.ConfigEntryState.LOADED
    assert "frontend_extra_module_url" not in hass.data


async def test_card_js_has_custom_cards_registration():
    """Test that the card JS registers itself in window.customCards."""
    content = CARD_PATH.read_text()
    assert "window.customCards" in content, "Card JS missing window.customCards registration"
    assert "recurring-todos-card" in content, "Card JS missing card type declaration"


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


async def test_card_registered_once_with_multiple_entries(hass: HomeAssistant):
    """Test that card JS URL is registered only once even with multiple entries."""
    hass.data["frontend_extra_module_url"] = set()
    hass.config.components.add("frontend")

    entry1 = _make_entry("entry_1", "List A")
    entry1.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    entry2 = _make_entry("entry_2", "List B")
    entry2.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    extra_urls = hass.data["frontend_extra_module_url"]
    assert CARD_URL_CACHE_BUST in extra_urls
    assert len(extra_urls) == 1


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
