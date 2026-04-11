# Recurring Todos - Home Assistant Integration

A custom Home Assistant integration for tracking recurring and one-off tasks/chores. Built on HA's native To-Do platform with added recurrence, overdue detection, and mobile notifications.

## Features

- **Recurring tasks** with full iCal RRULE support (daily, weekly, monthly, yearly, custom patterns)
- **One-off tasks** that work like standard to-do items
- **Full completion history** - every completion recorded, never pruned
- **Overdue detection** with attributes and events for automations
- **Mobile push notifications** via HA companion app - configurable lead time and reminder intervals
- **Custom Lovelace card** with friendly recurrence setup UI
- **Multiple task lists** - create separate lists for different categories
- **HACS compatible** for easy installation

## Installation

### HACS (Recommended)
1. Add this repository as a custom repository in HACS
2. Search for "Recurring Todos" and install
3. Restart Home Assistant

### Manual
1. Copy `custom_components/recurring_todos/` to your HA `custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **Recurring Todos**
3. Enter a name for your task list (e.g. "Household Chores")
4. Configure notification devices and timing in the integration options

## Usage

Tasks appear in HA's built-in **To-Do** panel. Use the custom Lovelace card for the full experience including recurrence setup.

### Lovelace Card
Add to your dashboard:
```yaml
type: custom:recurring-todos-card
entity: todo.household_chores
```

### Services
- `recurring_todos.complete_task` - Mark a task complete (triggers recurrence)
- `recurring_todos.snooze_task` - Push due date forward by N days

### Automations
Use the `recurring_todos_overdue` event as a trigger for custom automation flows.

## Documentation

- `CLAUDE.md` - LLM entry point: project layout, conventions, quick-start
- `docs/architecture.md` - Module responsibilities, data flow, design decisions
- `docs/api-reference.md` - Services, attributes, events, storage schema, RRULE examples

These docs are optimized for LLM consumption - structured, concise, no filler. Read these before diving into source code.

## Development

See `features.json` for the implementation task tracker.
