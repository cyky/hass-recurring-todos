"""Tests for config flow and options flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.recurring_todos.const import DOMAIN


async def test_user_flow_creates_entry(hass: HomeAssistant):
    """Test the user config flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Household Chores"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Household Chores"
    assert result["options"]["name"] == "Household Chores"


async def test_options_flow_saves_settings(
    hass: HomeAssistant, mock_setup_entry,
):
    """Test the options flow saves notification settings."""
    result = await hass.config_entries.options.async_init(
        mock_setup_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "notification_lead_time_hours": 48,
            "overdue_reminder_interval_hours": 6,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    assert mock_setup_entry.options["notification_lead_time_hours"] == 48
    assert mock_setup_entry.options["overdue_reminder_interval_hours"] == 6
