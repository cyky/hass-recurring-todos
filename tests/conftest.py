"""Shared fixtures and HA compatibility shims for tests."""

from __future__ import annotations

import sys
import types
from enum import StrEnum
from unittest.mock import AsyncMock, MagicMock


def _ensure_ha_shims() -> None:
    """Install minimal HA module shims if homeassistant is not importable."""
    try:
        from homeassistant.components.todo import TodoItemStatus  # noqa: F401

        return
    except ImportError:
        pass

    class TodoItemStatus(StrEnum):
        NEEDS_ACTION = "needs_action"
        COMPLETED = "completed"

    class TodoItem:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class TodoListEntity:
        pass

    class TodoListEntityFeature:
        CREATE_TODO_ITEM = 1
        UPDATE_TODO_ITEM = 2
        DELETE_TODO_ITEM = 4

    # homeassistant.components.todo
    ha_components_todo = types.ModuleType("homeassistant.components.todo")
    ha_components_todo.TodoItemStatus = TodoItemStatus
    ha_components_todo.TodoItem = TodoItem
    ha_components_todo.TodoListEntity = TodoListEntity
    ha_components_todo.TodoListEntityFeature = TodoListEntityFeature

    # homeassistant.const
    ha_const = types.ModuleType("homeassistant.const")
    mock_platform = MagicMock()
    mock_platform.TODO = "todo"
    ha_const.Platform = mock_platform

    # homeassistant.core
    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = MagicMock
    ha_core.ServiceCall = MagicMock
    ha_core.callback = lambda f: f

    # homeassistant.helpers.*
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_helpers_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_helpers_storage.Store = MagicMock
    ha_helpers_event = types.ModuleType("homeassistant.helpers.event")
    ha_helpers_event.async_track_time_interval = MagicMock()
    ha_helpers_entity_platform = types.ModuleType(
        "homeassistant.helpers.entity_platform"
    )
    ha_helpers_entity_platform.AddEntitiesCallback = MagicMock
    ha_helpers_entity_registry = types.ModuleType(
        "homeassistant.helpers.entity_registry"
    )
    ha_helpers_entity_registry.async_get = MagicMock()
    ha_helpers.storage = ha_helpers_storage
    ha_helpers.event = ha_helpers_event
    ha_helpers.entity_platform = ha_helpers_entity_platform
    ha_helpers.entity_registry = ha_helpers_entity_registry

    # homeassistant.helpers.schema_config_entry_flow
    ha_helpers_schema = types.ModuleType(
        "homeassistant.helpers.schema_config_entry_flow"
    )
    ha_helpers_schema.SchemaConfigFlowHandler = type(
        "SchemaConfigFlowHandler", (), {}
    )
    ha_helpers_schema.SchemaCommonFlowHandler = MagicMock
    ha_helpers_schema.SchemaFlowFormStep = MagicMock
    ha_helpers.schema_config_entry_flow = ha_helpers_schema

    # homeassistant.helpers.selector
    ha_helpers_selector = types.ModuleType("homeassistant.helpers.selector")
    for name in [
        "NumberSelector",
        "NumberSelectorConfig",
        "NumberSelectorMode",
        "SelectOptionDict",
        "SelectSelector",
        "SelectSelectorConfig",
        "TextSelector",
    ]:
        setattr(ha_helpers_selector, name, MagicMock)
    ha_helpers.selector = ha_helpers_selector

    # homeassistant.config_entries
    ha_config_entries = types.ModuleType("homeassistant.config_entries")
    ha_config_entries.ConfigEntry = MagicMock

    # Build parent modules
    ha = types.ModuleType("homeassistant")
    ha_components = types.ModuleType("homeassistant.components")
    ha_components.todo = ha_components_todo
    ha.components = ha_components
    ha.const = ha_const
    ha.core = ha_core
    ha.helpers = ha_helpers
    ha.config_entries = ha_config_entries

    sys.modules.update(
        {
            "homeassistant": ha,
            "homeassistant.components": ha_components,
            "homeassistant.components.todo": ha_components_todo,
            "homeassistant.const": ha_const,
            "homeassistant.core": ha_core,
            "homeassistant.config_entries": ha_config_entries,
            "homeassistant.helpers": ha_helpers,
            "homeassistant.helpers.storage": ha_helpers_storage,
            "homeassistant.helpers.event": ha_helpers_event,
            "homeassistant.helpers.entity_platform": ha_helpers_entity_platform,
            "homeassistant.helpers.entity_registry": ha_helpers_entity_registry,
            "homeassistant.helpers.schema_config_entry_flow": ha_helpers_schema,
            "homeassistant.helpers.selector": ha_helpers_selector,
        }
    )


_ensure_ha_shims()
