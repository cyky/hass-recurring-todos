"""Integration tests for the notification engine."""

from __future__ import annotations

from datetime import date, timedelta

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.recurring_todos.const import DOMAIN
from custom_components.recurring_todos.model import TaskItem
from custom_components.recurring_todos.notify import NotificationChecker


async def test_notification_sent_to_devices(
    hass: HomeAssistant,
):
    """Test that notifications are sent to configured devices."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test List",
        data={"name": "Test List"},
        options={
            "notify_devices": ["mobile_app_phone"],
            "notification_lead_time_hours": 48,
            "overdue_reminder_interval_hours": 12,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    store = hass.data[DOMAIN][entry.entry_id]
    yesterday = date.today() - timedelta(days=1)
    task = TaskItem(name="Overdue chore", due_date=yesterday)
    await store.async_add_item(entry.entry_id, task)

    # Register a mock notify service and get the calls list
    calls = async_mock_service(hass, "notify", "mobile_app_phone")

    checker = NotificationChecker(hass, entry)
    await checker._async_check_and_notify()

    assert len(calls) == 1
    assert calls[0].data["title"] == "Test List"


async def test_no_notification_without_devices(
    hass: HomeAssistant,
):
    """Test that no notifications are sent when no devices configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test List",
        data={"name": "Test List"},
        options={},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    store = hass.data[DOMAIN][entry.entry_id]
    yesterday = date.today() - timedelta(days=1)
    task = TaskItem(name="Overdue chore", due_date=yesterday)
    await store.async_add_item(entry.entry_id, task)

    # Register a mock notify service — should not be called
    calls = async_mock_service(hass, "notify", "mobile_app_phone")

    checker = NotificationChecker(hass, entry)
    await checker._async_check_and_notify()

    assert len(calls) == 0


async def test_rate_limiting(hass: HomeAssistant):
    """Test that rate limiting prevents duplicate notifications."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test List",
        data={"name": "Test List"},
        options={
            "notify_devices": ["mobile_app_phone"],
            "notification_lead_time_hours": 48,
            "overdue_reminder_interval_hours": 12,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    store = hass.data[DOMAIN][entry.entry_id]
    yesterday = date.today() - timedelta(days=1)
    task = TaskItem(name="Overdue chore", due_date=yesterday)
    await store.async_add_item(entry.entry_id, task)

    calls = async_mock_service(hass, "notify", "mobile_app_phone")

    checker = NotificationChecker(hass, entry)

    # First call should notify
    await checker._async_check_and_notify()
    assert len(calls) == 1

    # Second call immediately after should be rate limited
    await checker._async_check_and_notify()
    assert len(calls) == 1  # still 1, no second notification
