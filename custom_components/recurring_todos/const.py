"""Constants for the Recurring Todos integration."""

from homeassistant.const import Platform

DOMAIN = "recurring_todos"
PLATFORMS = [Platform.TODO]
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION = 1
EVENT_OVERDUE = f"{DOMAIN}_overdue"
OVERDUE_CHECK_INTERVAL = 300  # seconds
NOTIFICATION_CHECK_INTERVAL = 1800  # seconds (30 minutes)
SERVICE_COMPLETE_TASK = "complete_task"
SERVICE_SNOOZE_TASK = "snooze_task"
SERVICE_CREATE_TASK = "create_task"
SERVICE_UPDATE_TASK = "update_task"
SIGNAL_STORE_UPDATED = f"{DOMAIN}_store_updated"

# Options flow keys
CONF_DEFAULT_RECURRENCE = "default_recurrence"
CONF_NOTIFICATION_LEAD_TIME_HOURS = "notification_lead_time_hours"
CONF_OVERDUE_REMINDER_INTERVAL_HOURS = "overdue_reminder_interval_hours"
CONF_QUIET_HOURS_ENABLED = "quiet_hours_enabled"
CONF_QUIET_HOURS_START = "quiet_hours_start"
CONF_QUIET_HOURS_END = "quiet_hours_end"
CONF_NOTIFY_DEVICES = "notify_devices"
DEFAULT_QUIET_HOURS_START = "22:00:00"
DEFAULT_QUIET_HOURS_END = "08:00:00"

# Runtime data keys
DATA_STORE = "store"
DATA_ENTRY_IDS = "entry_ids"
DATA_NOTIFY_UNSUBS = "notify_unsubs"
