"""Debug services for Yeelight Pro."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    DOMAIN,
)
from .debug_push_service import async_register_debug_push_services
from .debug_runtime import ATTR_ENTRY_ID, debug_coordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_DEBUG_EMIT_EVENT_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Required(ATTR_SOURCE_DEVICE_ID): vol.Any(int, cv.string),
    vol.Required(ATTR_COMPONENT_ID): cv.string,
    vol.Required(ATTR_EVENT_TYPE): cv.string,
    vol.Optional(ATTR_EVENT_ATTRIBUTES, default={}): dict,
})


def async_register_debug_event_service(hass: HomeAssistant) -> None:
    """Register guarded debug services."""

    async def handle_debug_emit_event(call: ServiceCall) -> None:
        """向 HA 事件总线发射调试 Yeelight Pro 设备事件。"""
        entry_id = call.data.get(ATTR_ENTRY_ID)
        coordinator = debug_coordinator(hass, entry_id=entry_id)
        if coordinator is None:
            raise HomeAssistantError("Yeelight Pro debug mode is disabled or entry_id is invalid")
        event = await coordinator.async_handle_runtime_event(call.data)
        _LOGGER.info(
            "Emitted debug Yeelight Pro event: event_type=%s",
            event.event_type,
        )

    async_register_admin_service(
        hass,
        DOMAIN,
        "debug_emit_event",
        handle_debug_emit_event,
        schema=SERVICE_DEBUG_EMIT_EVENT_SCHEMA,
    )
    async_register_debug_push_services(hass)


def _debug_coordinator(hass: HomeAssistant, *, entry_id: str | None = None) -> Any | None:
    """Compatibility wrapper for existing tests and local diagnostics."""
    return debug_coordinator(hass, entry_id=entry_id)
