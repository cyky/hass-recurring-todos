# Recurring Todos — HA Custom Integration

## Purpose
Track recurring/one-off tasks in Home Assistant. Extends HA Todo platform w/ iCal RRULE recurrence, completion history, overdue detection, mobile push.

## Domain
`recurring_todos` — prefixes all services, events, storage keys.

## Directory Layout
```
custom_components/recurring_todos/
  __init__.py      # Integration setup (async_setup_entry/async_unload_entry)
  const.py         # DOMAIN, PLATFORMS, storage constants
  model.py         # TaskItem dataclass with to_dict/from_dict
  store.py         # Storage layer (homeassistant.helpers.storage.Store)
  config_flow.py   # Config + options flow (SchemaConfigFlowHandler)
  todo.py          # TodoListEntity implementation
  recurrence.py    # RRULE parsing via python-dateutil
  notify.py        # Periodic notification checker
  services.yaml    # Service schemas
  strings.json     # UI strings
  translations/en.json
```

## Key Dependencies
- `python-dateutil` — RRULE parsing (rrulestr)
- `homeassistant.components.todo` — TodoListEntity, TodoItem, TodoItemStatus
- `homeassistant.helpers.storage` — Store for JSON persistence

## Data Model
`TaskItem` dataclass in `model.py`:
- `uid`, `name`, `description`, `status` (TodoItemStatus), `due_date`, `rrule` (iCal string), `completion_history` (list of dicts, never pruned), `created_at`

## Key Patterns
- 1 config entry = 1 task list. Multiple lists supported.
- Runtime data: `hass.data[DOMAIN][entry.entry_id]`
- Recurring: complete → record history → next due from RRULE → reset NEEDS_ACTION
- One-off (rrule=None): stay completed
- Storage v1, keyed by config entry ID

## Services
- `recurring_todos.complete_task` — mark done, trigger recurrence
- `recurring_todos.snooze_task` — push due date forward N days

## Events
- `recurring_todos_overdue` — fired when tasks overdue

## Development
```bash
# Symlink into HA for dev
ln -s $(pwd)/custom_components/recurring_todos ~/.homeassistant/custom_components/recurring_todos

# Run tests
pytest tests/

# Validate syntax (no HA runtime needed)
python -c "import ast; ast.parse(open('custom_components/recurring_todos/model.py').read())"
```

## Task Tracker
See `features.json` for status/dependency graph.

## Conventions
- Python 3.12+, `from __future__ import annotations`
- Dataclasses over dicts for internal models
- ISO 8601 strings for datetime serialization in storage
- HA async patterns throughout (async_*, hass.async_add_executor_job for blocking)