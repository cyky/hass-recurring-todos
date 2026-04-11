"""Config flow for Recurring Todos."""

from __future__ import annotations

from typing import Any, Mapping

import voluptuous as vol

from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)

from .const import DOMAIN

CONF_NAME = "name"

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
    }
)

CONFIG_FLOW = {
    "user": SchemaFlowFormStep(schema=CONFIG_SCHEMA),
}


class RecurringTodosConfigFlow(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Recurring Todos."""

    config_flow = CONFIG_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return str(options[CONF_NAME])
