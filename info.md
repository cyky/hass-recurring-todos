# Recurring Todos

Track recurring and one-off tasks in Home Assistant with iCal RRULE recurrence, mobile push notifications, and a custom Lovelace card.

## Features

- Todo platform integration — tasks appear as standard HA todo entities
- iCal RRULE recurrence — daily, weekly, monthly, yearly, or custom patterns
- Overdue detection — fires events for automations, exposes overdue count
- Push notifications — configurable lead time and reminder intervals
- Custom Lovelace card — task list with recurrence picker and completion history

## Installation

1. Install via HACS or copy `custom_components/recurring_todos/` to your HA config directory
2. Restart Home Assistant
3. Add via **Settings > Devices & Services > Add Integration > Recurring Todos**

The Lovelace card registers automatically — no manual resource configuration needed.
