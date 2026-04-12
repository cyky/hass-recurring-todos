# API Reference — Recurring Todos

## Services

### `recurring_todos.complete_task`

Mark a task as completed. Recurring tasks advance to next due date; one-off tasks stay completed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_id` | string | yes | Todo list entity (e.g. `todo.household_chores`) |
| `task_uid` | string | yes | Task UUID |

### `recurring_todos.snooze_task`

Push a task's due date forward.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `entity_id` | string | yes | — | Todo list entity |
| `task_uid` | string | yes | — | Task UUID |
| `days` | int | no | 1 | Days to snooze (1–365) |

## Entity Attributes

Entity domain: `todo`, integration: `recurring_todos`

| Attribute | Type | Description |
|-----------|------|-------------|
| `todo_items` | list[TodoItem] | Standard HA todo items (uid, summary, description, status, due) |
| `overdue_count` | int | Number of overdue tasks |
| `overdue_tasks` | list[dict] | Overdue tasks: `{uid, name, due_date}` |

## Events

### `recurring_todos_overdue`

Fired every 5 minutes when overdue tasks exist. Usable as automation trigger.

| Field | Type | Description |
|-------|------|-------------|
| `entity_id` | string | Todo list entity |
| `entry_id` | string | Config entry ID |
| `overdue_tasks` | list[dict] | `{uid, name, due_date, days_overdue}` |
| `overdue_count` | int | Total overdue count |

## Config Entry Options

Set via Settings > Devices & Services > Recurring Todos > Configure.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `default_recurrence` | string | `""` | RRULE template for new tasks |
| `notification_lead_time_hours` | int | 24 | Hours before due to first notify |
| `overdue_reminder_interval_hours` | int | 12 | Hours between re-notifications |
| `notify_devices` | list[string] | `[]` | mobile_app notify service names |

## TaskItem Model

| Field | Type | Description |
|-------|------|-------------|
| `uid` | string | UUID v4, auto-generated |
| `name` | string | Task name |
| `description` | string\|null | Optional description |
| `status` | `needs_action`\|`completed` | Current state |
| `due_date` | date\|null | ISO 8601 date |
| `rrule` | string\|null | iCal RRULE (null = one-off) |
| `completion_history` | list[dict] | `[{completed_at: ISO8601}]`, never pruned |
| `created_at` | string | ISO 8601 datetime |

Computed: `is_overdue` — `True` when `due_date < today` and `status != completed`

## RRULE Examples

| Pattern | RRULE |
|---------|-------|
| Daily | `FREQ=DAILY` |
| Every 3 days | `FREQ=DAILY;INTERVAL=3` |
| Weekdays | `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR` |
| Weekly on Monday | `FREQ=WEEKLY;BYDAY=MO` |
| Biweekly | `FREQ=WEEKLY;INTERVAL=2` |
| Monthly (same day) | `FREQ=MONTHLY` |
| Monthly 1st | `FREQ=MONTHLY;BYMONTHDAY=1` |
| Quarterly | `FREQ=MONTHLY;INTERVAL=3` |
| Yearly | `FREQ=YEARLY` |
