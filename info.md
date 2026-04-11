# Recurring Todos

Track recurring and one-off tasks in Home Assistant with iCal RRULE recurrence, mobile push notifications, and a custom Lovelace card.

## Features

- **Todo platform integration** — tasks appear as standard HA todo entities
- **iCal RRULE recurrence** — daily, weekly, monthly, yearly, or custom patterns
- **Overdue detection** — fires events for automations, exposes overdue count as entity attributes
- **Push notifications** — configurable lead time and reminder intervals to mobile devices
- **Custom Lovelace card** — task list with add/edit forms, recurrence UI, completion history
- **Services** — `complete_task` (triggers recurrence) and `snooze_task` (push due date forward)

## Installation

1. Install via HACS or copy `custom_components/recurring_todos/` to your HA config directory
2. Restart Home Assistant
3. Add the integration via Settings > Devices & Services > Add Integration > Recurring Todos
4. Add the Lovelace card as a custom resource: `/local/community/recurring_todos/www/recurring-todos-card.js`

## Configuration

Each config entry creates one task list. Use the options flow (Settings > Devices & Services > Recurring Todos > Configure) to set:

- Default recurrence rule (RRULE template)
- Notification lead time (hours before due)
- Overdue reminder interval (hours between reminders)
- Notification devices (mobile_app services)
