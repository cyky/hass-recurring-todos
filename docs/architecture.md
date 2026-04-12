# Architecture — Recurring Todos

## Module Map

| File | Purpose |
|------|---------|
| `const.py` | Domain name, platform list, storage keys, service names, option keys, intervals |
| `model.py` | `TaskItem` dataclass — fields, serialization, `is_overdue` property |
| `store.py` | `RecurringTodosStore` — wraps HA `Store` for JSON persistence, CRUD by entry ID |
| `recurrence.py` | `calculate_next_due()` — RRULE parsing via python-dateutil |
| `config_flow.py` | `SchemaConfigFlowHandler` — user step (list name) + options flow (recurrence/notification settings) |
| `todo.py` | `RecurringTodosListEntity` — TodoListEntity with CRUD, overdue event firing |
| `notify.py` | `NotificationChecker` — periodic push notifications for due/overdue tasks |
| `__init__.py` | Entry setup/teardown, service registration (complete_task, snooze_task) |
| `www/recurring-todos-card.js` | Custom Lovelace card — task list UI, recurrence form, RRULE builder |

## Data Flow: Task Creation

```
User (Lovelace card or HA UI)
  → todo.add_item service
  → RecurringTodosListEntity.async_create_todo_item()
  → TaskItem(name, due_date, status=NEEDS_ACTION)
  → store.async_add_item(entry_id, task)
  → Store.async_save() → .storage/recurring_todos.storage
```

## Data Flow: Completion with Recurrence

```
User completes task
  → recurring_todos.complete_task service (or todo entity update)
  → If task.rrule is set:
      1. Append {completed_at} to task.completion_history
      2. calculate_next_due(rrule, current_due_date) → next date
      3. task.due_date = next date
      4. task.status = NEEDS_ACTION (reset)
  → If no rrule:
      task.status = COMPLETED (stays done)
  → store.async_update_item() → persist
```

## Data Flow: Notification Cycle

```
async_track_time_interval (every 30 min)
  → NotificationChecker._async_check_and_notify()
  → Read entry.options: devices, lead_time, interval
  → For each task in store.get_items(entry_id):
      _should_notify(task, now, options)?
        - Has due_date? Not completed?
        - Within lead_time window or overdue?
        - Not recently notified (rate limit)?
      → Yes: hass.services.async_call("notify", device, {title, message})
      → Update _last_notified[task.uid] = now
```

## Data Flow: Overdue Detection

```
async_track_time_interval (every 5 min, in todo.py)
  → _async_check_overdue()
  → Filter tasks where is_overdue (due_date < today, not completed)
  → If any: hass.bus.async_fire("recurring_todos_overdue", payload)
  → async_write_ha_state() to update entity attributes
```

## Storage Schema (v1)

```json
{
  "<config_entry_id>": [
    {
      "uid": "uuid4",
      "name": "string",
      "description": "string|null",
      "status": "needs_action|completed",
      "due_date": "YYYY-MM-DD|null",
      "rrule": "FREQ=...|null",
      "completion_history": [{"completed_at": "ISO8601"}],
      "created_at": "ISO8601"
    }
  ]
}
```

File: `.storage/recurring_todos.storage`

## Runtime Data Layout

```
hass.data["recurring_todos"] = {
    "<entry_id>": RecurringTodosStore,
    "<entry_id>_notify_unsub": Callable,  # cancel notification checker
}
```

## Key Design Decisions

1. **1 config entry = 1 task list** — multiple lists via multiple entries, each with own options
2. **Completion history never pruned** — full audit trail, no TTL
3. **In-memory last_notified** — lost on restart (acceptable: re-notifies once after restart)
4. **Options read fresh each cycle** — no update listener needed, changes take effect next check
5. **Overdue events separate from notifications** — events serve automations, notifications serve humans
6. **No HA runtime dependency for tests** — conftest shims HA modules for standalone pytest
