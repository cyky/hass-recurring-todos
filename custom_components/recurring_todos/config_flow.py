"""Config flow for Recurring Todos."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

import voluptuous as vol

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TimeSelector,
)

from .const import (
    CONF_DEFAULT_RECURRENCE,
    CONF_NOTIFY_DEVICES,
    CONF_NOTIFICATION_LEAD_TIME_HOURS,
    CONF_OVERDUE_REMINDER_INTERVAL_HOURS,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    DOMAIN,
)

CONF_NAME = "name"

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
    }
)

async def _validate_user_input(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate user input and set unique_id to prevent duplicate lists."""
    name = user_input[CONF_NAME]
    await handler.parent_handler.async_set_unique_id(name.lower())
    handler.parent_handler._abort_if_unique_id_configured()
    return user_input


CONFIG_FLOW = {
    "user": SchemaFlowFormStep(
        schema=CONFIG_SCHEMA,
        validate_user_input=_validate_user_input,
    ),
}


@callback
def _async_get_options_schema(
    hass: HomeAssistant,
    options: MappingProxyType[str, Any],
) -> vol.Schema:
    """Build options schema with dynamic notify device list."""
    notify_services: list[SelectOptionDict] = []
    for service_name in hass.services.async_services_for_domain("notify"):
        if service_name.startswith("mobile_app_"):
            device_name = service_name.removeprefix("mobile_app_")
            notify_services.append(
                SelectOptionDict(
                    label=device_name.replace("_", " ").title(),
                    value=service_name,
                )
            )

    return vol.Schema(
        {
            vol.Optional(
                CONF_DEFAULT_RECURRENCE,
                description={
                    "suggested_value": options.get(CONF_DEFAULT_RECURRENCE, "")
                },
            ): TextSelector(),
            vol.Optional(
                CONF_NOTIFICATION_LEAD_TIME_HOURS,
                description={
                    "suggested_value": options.get(
                        CONF_NOTIFICATION_LEAD_TIME_HOURS, 24
                    )
                },
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=168, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_QUIET_HOURS_ENABLED,
                description={
                    "suggested_value": options.get(
                        CONF_QUIET_HOURS_ENABLED, True
                    )
                },
            ): BooleanSelector(),
            vol.Optional(
                CONF_QUIET_HOURS_START,
                description={
                    "suggested_value": options.get(
                        CONF_QUIET_HOURS_START, DEFAULT_QUIET_HOURS_START
                    )
                },
            ): TimeSelector(),
            vol.Optional(
                CONF_QUIET_HOURS_END,
                description={
                    "suggested_value": options.get(
                        CONF_QUIET_HOURS_END, DEFAULT_QUIET_HOURS_END
                    )
                },
            ): TimeSelector(),
            vol.Optional(
                CONF_OVERDUE_REMINDER_INTERVAL_HOURS,
                description={
                    "suggested_value": options.get(
                        CONF_OVERDUE_REMINDER_INTERVAL_HOURS, 12
                    )
                },
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=168, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_NOTIFY_DEVICES,
                description={
                    "suggested_value": options.get(CONF_NOTIFY_DEVICES, [])
                },
            ): SelectSelector(
                SelectSelectorConfig(options=notify_services, multiple=True)
            ),
        }
    )


async def _async_options_schema(
    handler: SchemaCommonFlowHandler,
) -> vol.Schema:
    """Return options schema, called by SchemaFlowFormStep."""
    return _async_get_options_schema(
        handler.parent_handler.hass,
        handler.parent_handler.config_entry.options,
    )


OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(_async_options_schema),
}


class RecurringTodosConfigFlow(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Recurring Todos."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return str(options[CONF_NAME])
