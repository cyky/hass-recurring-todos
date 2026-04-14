# Recurring Todos for Home Assistant

A custom Home Assistant integration for tracking recurring and one-off tasks. Built on HA's native Todo platform with iCal RRULE recurrence, mobile push notifications, and a custom Lovelace card.

## Features

- **Recurring tasks** with iCal RRULE support (daily, weekly, monthly, yearly, custom)
- **One-off tasks** that work like standard todo items
- **Completion history** recorded on every completion, never pruned
- **Overdue detection** with `recurring_todos_overdue` events and `overdue_count` attribute
- **Push notifications** with configurable lead time and reminder intervals
- **Custom Lovelace card** with recurrence picker and completion history viewer
- **Multiple task lists** via separate config entries
- **HACS compatible**

## Installation

### HACS (recommended)

1. Open HACS → three-dot menu → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Click **Download**, then restart Home Assistant

### Manual

Copy `custom_components/recurring_todos/` into your HA `config/custom_components/` directory and restart.

## Setup

1. **Settings > Devices & Services > Add Integration** → search **Recurring Todos**
2. Enter a name for your task list (e.g., "Household Chores")
3. A `todo.*` entity is created that works with HA's built-in todo UI

The custom Lovelace card registers automatically. Add it to any dashboard:

```yaml
type: custom:recurring-todos-card
entity: todo.household_chores
```

### Card screenshots

| Task list | Add/edit form | Recurrence picker |
|:---------:|:-------------:|:-----------------:|
| ![Task list](docs/images/card-list.png) | ![Add form](docs/images/card-add-form.png) | ![Recurrence](docs/images/card-recurrence.png) |

| Delete confirmation | Completion history |
|:-------------------:|:------------------:|
| ![Delete confirm](docs/images/card-delete-confirm.png) | ![History](docs/images/card-history.png) |

## Configuration

Options flow: **Settings > Devices & Services > Recurring Todos > Configure**

| Option | Default | Description |
|--------|---------|-------------|
| Default recurrence | *(empty)* | RRULE template for new tasks (e.g., `FREQ=WEEKLY`) |
| Notification lead time | 24h | Hours before due date to start notifying |
| Overdue reminder interval | 12h | Hours between re-notifications |
| Notification devices | *(none)* | Mobile app services for push notifications |

## Services

The integration registers four services: `complete_task`, `snooze_task`, `create_task`, and `update_task`. See [docs/api-reference.md](docs/api-reference.md) for parameters and examples.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest tests/
```

For local HA testing with Docker: `docker compose up -d` → http://localhost:8123

See [docs/architecture.md](docs/architecture.md) for module responsibilities and data flow.

## License

MIT
