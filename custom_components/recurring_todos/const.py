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

# Options flow keys
CONF_DEFAULT_RECURRENCE = "default_recurrence"
CONF_NOTIFICATION_LEAD_TIME_HOURS = "notification_lead_time_hours"
CONF_OVERDUE_REMINDER_INTERVAL_HOURS = "overdue_reminder_interval_hours"
CONF_NOTIFY_DEVICES = "notify_devices"
