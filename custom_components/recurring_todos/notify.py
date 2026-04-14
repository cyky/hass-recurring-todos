"""Notification engine for Recurring Todos."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.todo import TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NOTIFICATION_LEAD_TIME_HOURS,
    CONF_NOTIFY_DEVICES,
    CONF_OVERDUE_REMINDER_INTERVAL_HOURS,
    DATA_STORE,
    DOMAIN,
    NOTIFICATION_CHECK_INTERVAL,
)
from .model import TaskItem

_LOGGER = logging.getLogger(__name__)


class NotificationChecker:
    """Periodically checks for due/overdue tasks and sends push notifications."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._last_notified: dict[str, datetime] = {}

    async def start(self) -> Callable[[], None]:
        """Start the periodic notification checker and return the unsub callable."""
        unsub = async_track_time_interval(
            self._hass,
            self._async_check_and_notify,
            timedelta(seconds=NOTIFICATION_CHECK_INTERVAL),
        )
        await self._async_check_and_notify()
        return unsub

    async def _async_check_and_notify(
        self, _now: datetime | None = None
    ) -> None:
        """Check all tasks and send notifications as needed."""
        options = self._entry.options
        devices: list[str] = options.get(CONF_NOTIFY_DEVICES, [])
        if not devices:
            return

        domain_data = self._hass.data.get(DOMAIN)
        if domain_data is None:
            return
        store = domain_data.get(DATA_STORE)
        if store is None:
            return

        now = dt_util.now()
        tasks: list[TaskItem] = store.get_items(self._entry.entry_id)

        for task in tasks:
            if not self._should_notify(task, now, options):
                continue

            title, message = self._build_message(task)
            for device in devices:
                await self._send_notification(device, title, message)

            self._last_notified[task.uid] = now

    def _should_notify(
        self,
        task: TaskItem,
        now: datetime,
        options: Mapping[str, Any],
    ) -> bool:
        """Determine if a task warrants a notification right now."""
        if task.due_date is None:
            return False
        if task.status == TodoItemStatus.COMPLETED:
            return False

        lead_time = options.get(CONF_NOTIFICATION_LEAD_TIME_HOURS, 24)
        reminder_interval = options.get(CONF_OVERDUE_REMINDER_INTERVAL_HOURS, 12)

        due_datetime = dt_util.start_of_local_day(task.due_date)
        notify_threshold = due_datetime - timedelta(hours=lead_time)

        if now < notify_threshold:
            return False

        last = self._last_notified.get(task.uid)
        if last is not None and (now - last) < timedelta(hours=reminder_interval):
            return False

        return True

    def _build_message(self, task: TaskItem) -> tuple[str, str]:
        """Build notification title and message for a task."""
        title = self._entry.title
        today = dt_util.now().date()

        if task.due_date is None:
            return title, f"{task.name} needs attention"

        delta_days = (today - task.due_date).days

        if delta_days > 0:
            message = (
                f"{task.name} is {delta_days} day{'s' if delta_days != 1 else ''} "
                f"overdue (due {task.due_date.isoformat()})"
            )
        elif delta_days == 0:
            message = f"{task.name} is due today"
        else:
            days_until = -delta_days
            message = (
                f"{task.name} is due in {days_until} "
                f"day{'s' if days_until != 1 else ''} "
                f"({task.due_date.isoformat()})"
            )

        return title, message

    async def _send_notification(
        self, device: str, title: str, message: str
    ) -> None:
        """Send a push notification to a single device."""
        try:
            await self._hass.services.async_call(
                "notify",
                device,
                {"title": title, "message": message},
            )
        except ServiceNotFound:
            _LOGGER.warning(
                "Notification service 'notify.%s' not found", device
            )
