"""Constants for the Recurring Todos integration."""

from homeassistant.const import Platform

DOMAIN = "recurring_todos"
PLATFORMS = [Platform.TODO]
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION = 1
