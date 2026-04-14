# Architecture

## Module Map

| File | Purpose |
|------|---------|
| `const.py` | Domain, platform list, storage keys, service/option/interval constants |
| `model.py` | `TaskItem` dataclass — fields, serialization, `is_overdue` |
| `store.py` | `RecurringTodosStore` — HA `Store` wrapper, CRUD by entry ID |
| `recurrence.py` | `calculate_next_due()` — RRULE parsing via python-dateutil |
| `config_flow.py` | `SchemaConfigFlowHandler` — user step + options flow |
| `todo.py` | `RecurringTodosListEntity` — TodoListEntity, CRUD, overdue event firing |
| `notify.py` | `NotificationChecker` — periodic push for due/overdue tasks |
| `__init__.py` | Entry setup/teardown, service registration |
| `www/recurring-todos-card.js` | Custom Lovelace card |

## Data Flow

**Task creation:**
```
User → todo.add_item → RecurringTodosListEntity.async_create_todo_item()
  → TaskItem(name, due_date, status=NEEDS_ACTION)
  → store.async_add_item(entry_id, task) → .storage/recurring_todos.storage
```

**Completion with recurrence:**
```
complete_task service (or entity update)
  → If rrule: append to completion_history, calculate_next_due(), reset NEEDS_ACTION
  → If no rrule: status = COMPLETED (stays done)
  → store.async_update_item() → persist
```

**Notifications** (every 30 min):
```
NotificationChecker._async_check_and_notify()
  → For each task: within lead_time or overdue? Not recently notified?
  → Yes: hass.services.async_call("notify", device, {title, message})
```

**Overdue detection** (every 5 min):
```
_async_check_overdue() → filter tasks where is_overdue
  → Fire "recurring_todos_overdue" event, update entity state
```

## Runtime Data

```
hass.data["recurring_todos"] = {
    "store": RecurringTodosStore,
    "entry_ids": set[str],
    "notify_unsubs": dict[str, Callable],
    "card_registered": bool,
}
```

## Storage Schema (v1)

File: `.storage/recurring_todos.storage`

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

## Design Decisions

1. **1 config entry = 1 task list** — multiple lists via multiple entries, each with own options
2. **Completion history never pruned** — full audit trail
3. **In-memory last_notified** — lost on restart (re-notifies once, acceptable)
4. **Options read fresh each cycle** — no update listener needed
5. **Overdue events separate from notifications** — events for automations, notifications for humans
