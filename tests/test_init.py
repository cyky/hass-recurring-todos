"""Tests for integration setup and teardown."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.recurring_todos.const import (
    DOMAIN,
    SERVICE_COMPLETE_TASK,
    SERVICE_SNOOZE_TASK,
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


async def test_services_registered(hass: HomeAssistant, mock_setup_entry):
    """Test that custom services are registered after setup."""
    assert hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK)
    assert hass.services.has_service(DOMAIN, SERVICE_SNOOZE_TASK)


async def test_services_removed_on_last_unload(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that services are removed when the last entry is unloaded."""
    await hass.config_entries.async_unload(mock_setup_entry.entry_id)
    assert not hass.services.has_service(DOMAIN, SERVICE_COMPLETE_TASK)
    assert not hass.services.has_service(DOMAIN, SERVICE_SNOOZE_TASK)


async def test_notification_checker_unsub_stored(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test that notification checker unsub is stored in hass.data."""
    notify_unsubs = hass.data[DOMAIN]["notify_unsubs"]
    assert mock_setup_entry.entry_id in notify_unsubs
    assert callable(notify_unsubs[mock_setup_entry.entry_id])
