"""Shared fixtures for Recurring Todos tests."""

from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.recurring_todos.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture(autouse=True)
def mock_frontend(hass: HomeAssistant) -> None:
    """Mark frontend as loaded and seed its data key.

    Prevents HA from trying to load the real frontend component (which needs
    the hass_frontend package) while still allowing add_extra_js_url to work.
    """
    hass.config.components.add("frontend")
    hass.data.setdefault("frontend_extra_module_url", set())


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for recurring_todos."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test List",
        data={"name": "Test List"},
        options={},
        unique_id="test_entry_1",
        version=1,
    )


@pytest.fixture
async def mock_setup_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_frontend
) -> MockConfigEntry:
    """Set up a config entry and return it."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
