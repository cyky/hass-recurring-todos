# API Reference

## Services

### `recurring_todos.complete_task`

Mark a task as completed. Recurring tasks advance to next due date; one-off tasks stay completed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_id` | string | yes | Todo list entity |
| `task_uid` | string | yes | Task UUID |

### `recurring_todos.snooze_task`

Push a task's due date forward.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `entity_id` | string | yes | — | Todo list entity |
| `task_uid` | string | yes | — | Task UUID |
| `days` | int | no | 1 | Days to snooze (1-365) |

### `recurring_todos.create_task`

Create a new task with optional recurrence.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_id` | string | yes | Todo list entity |
| `name` | string | yes | Task name |
| `description` | string | no | Task description |
| `due_date` | string | no | ISO 8601 date |
| `rrule` | string | no | iCal RRULE string |

### `recurring_todos.update_task`

Update an existing task. Only provided fields are changed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_id` | string | yes | Todo list entity |
| `task_uid` | string | yes | Task UUID |
| `name` | string | no | New task name |
| `description` | string | no | New description |
| `due_date` | string | no | New due date (ISO 8601) |
| `rrule` | string | no | New RRULE (empty string to remove) |

## Entity Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `todo_items` | list | All tasks: `{uid, summary, description, status, due, rrule}` |
| `overdue_count` | int | Number of overdue tasks |
| `overdue_tasks` | list | Overdue tasks: `{uid, name, due_date}` |
| `tasks_detail` | list | Per-task metadata: `{uid, name, rrule, completion_count, completion_history}` |

## Events

### `recurring_todos_overdue`

Fired every 5 minutes when overdue tasks exist.

| Field | Type | Description |
|-------|------|-------------|
| `entity_id` | string | Todo list entity |
| `entry_id` | string | Config entry ID |
| `overdue_tasks` | list | `{uid, name, due_date, days_overdue}` |
| `overdue_count` | int | Total overdue count |

## Config Options

Set via **Settings > Devices & Services > Recurring Todos > Configure**.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `default_recurrence` | string | `""` | RRULE template for new tasks |
| `notification_lead_time_hours` | int | 24 | Hours before due to first notify |
| `overdue_reminder_interval_hours` | int | 12 | Hours between re-notifications |
| `notify_devices` | list | `[]` | `notify.*` service names |

## RRULE Examples

| Pattern | RRULE |
|---------|-------|
| Daily | `FREQ=DAILY` |
| Every 3 days | `FREQ=DAILY;INTERVAL=3` |
| Weekdays | `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR` |
| Weekly on Monday | `FREQ=WEEKLY;BYDAY=MO` |
| Biweekly | `FREQ=WEEKLY;INTERVAL=2` |
| Monthly on same day | `FREQ=MONTHLY` |
| Quarterly | `FREQ=MONTHLY;INTERVAL=3` |
| Yearly | `FREQ=YEARLY` |
