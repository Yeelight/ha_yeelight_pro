"""Area registry services for Yeelight Pro."""

from __future__ import annotations

import logging
from collections.abc import Iterable

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    area_registry as ar,
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_AREA_ID = "area_id"
ATTR_DEVICES = "devices"
ATTR_GATEWAY_ID = "gateway_id"

SERVICE_ASSIGN_AREAS = "assign_areas"
SERVICE_AUTO_ASSIGN_AREAS = "auto_assign_areas"

ERROR_AREA_NOT_FOUND = "Requested Home Assistant area does not exist"
ERROR_GATEWAY_NOT_FOUND = "Requested gateway device does not exist"
ERROR_GATEWAY_NOT_YEELIGHT = "Requested gateway device is not a Yeelight Pro device"
ERROR_DEVICE_REFERENCE_INVALID = (
    "Device reference is not a device registry id or entity id"
)
ERROR_DEVICE_REFERENCE_NOT_YEELIGHT = (
    "Device reference is not a Yeelight Pro device"
)

SERVICE_ASSIGN_AREAS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICES): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_AREA_ID): cv.string,
    }
)

SERVICE_AUTO_ASSIGN_AREAS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_GATEWAY_ID): cv.string,
    }
)

_AREA_KEYWORDS = {
    "客厅": "客厅",
    "卧室": "卧室",
    "主卧": "主卧",
    "次卧": "次卧",
    "厨房": "厨房",
    "餐厅": "餐厅",
    "书房": "书房",
    "阳台": "阳台",
    "卫生间": "卫生间",
    "浴室": "浴室",
    "走廊": "走廊",
    "玄关": "玄关",
    "工作区": "工作区",
}


def async_register_area_services(hass: HomeAssistant) -> None:
    """Register admin-only HA area registry helper services."""

    async def handle_assign_areas(call: ServiceCall) -> None:
        """Assign HA areas for device registry ids or entity ids."""
        device_registry = dr.async_get(hass)
        area_registry = ar.async_get(hass)
        entity_registry = er.async_get(hass)

        area_id = call.data[ATTR_AREA_ID]
        if area_registry.async_get_area(area_id) is None:
            raise ServiceValidationError(ERROR_AREA_NOT_FOUND)

        device_ids = _resolve_device_references(
            device_registry,
            entity_registry,
            call.data[ATTR_DEVICES],
        )
        for device_id in device_ids:
            device_registry.async_update_device(device_id, area_id=area_id)

        _LOGGER.info(
            "Assigned %s Yeelight Pro devices to HA area %s",
            len(device_ids),
            area_id,
        )

    async def handle_auto_assign_areas(call: ServiceCall) -> None:
        """Assign HA areas based on existing device names."""
        device_registry = dr.async_get(hass)
        area_registry = ar.async_get(hass)
        gateway_id = call.data.get(ATTR_GATEWAY_ID)
        gateway_device = device_registry.async_get(gateway_id) if gateway_id else None
        if gateway_id and gateway_device is None:
            raise ServiceValidationError(ERROR_GATEWAY_NOT_FOUND)
        if gateway_device is not None and not _is_yeelight_device(gateway_device):
            raise ServiceValidationError(ERROR_GATEWAY_NOT_YEELIGHT)

        area_map = {area.name: area.id for area in area_registry.async_list_areas()}
        assigned_count = 0
        created_area_count = 0
        skipped_count = 0

        for device in device_registry.devices.values():
            if not _is_yeelight_device(device):
                continue
            if gateway_id and getattr(device, "via_device_id", None) != gateway_id:
                continue

            device_name = device.name or device.name_by_user or ""
            area_name = _area_name_for_device(device_name)
            if area_name is None:
                skipped_count += 1
                continue

            area_id = area_map.get(area_name)
            if area_id is None:
                new_area = area_registry.async_create(area_name)
                area_id = new_area.id
                area_map[area_name] = area_id
                created_area_count += 1
                _LOGGER.info("Created HA area %s for Yeelight Pro assignment", area_name)

            if getattr(device, "area_id", None) == area_id:
                skipped_count += 1
                continue

            device_registry.async_update_device(device.id, area_id=area_id)
            assigned_count += 1

        _LOGGER.info(
            "Auto-assigned %s Yeelight Pro devices to HA areas "
            "(created_areas=%s skipped=%s)",
            assigned_count,
            created_area_count,
            skipped_count,
        )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_ASSIGN_AREAS,
        handle_assign_areas,
        schema=SERVICE_ASSIGN_AREAS_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_AUTO_ASSIGN_AREAS,
        handle_auto_assign_areas,
        schema=SERVICE_AUTO_ASSIGN_AREAS_SCHEMA,
    )


def _resolve_device_references(
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    references: Iterable[str],
) -> list[str]:
    """Resolve HA device registry ids and entity ids to unique device ids."""
    device_ids: list[str] = []
    seen: set[str] = set()

    for reference in references:
        device_id = _device_id_from_reference(
            device_registry,
            entity_registry,
            reference,
        )
        if device_id in seen:
            continue
        seen.add(device_id)
        device_ids.append(device_id)

    if not device_ids:
        raise ServiceValidationError("No valid devices were provided")
    return device_ids


def _device_id_from_reference(
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    reference: str,
) -> str:
    """Resolve one service device reference."""
    device = device_registry.async_get(reference)
    if device is not None:
        if not _is_yeelight_device(device):
            raise ServiceValidationError(ERROR_DEVICE_REFERENCE_NOT_YEELIGHT)
        return reference

    registry_entry = entity_registry.async_get(reference)
    device_id = getattr(registry_entry, "device_id", None)
    if not isinstance(device_id, str):
        raise ServiceValidationError(ERROR_DEVICE_REFERENCE_INVALID)

    resolved_device_id: str = device_id
    device = device_registry.async_get(resolved_device_id)
    if device is not None:
        if not _is_yeelight_device(device):
            raise ServiceValidationError(ERROR_DEVICE_REFERENCE_NOT_YEELIGHT)
        return resolved_device_id

    raise ServiceValidationError(ERROR_DEVICE_REFERENCE_INVALID)


def _area_name_for_device(device_name: str) -> str | None:
    """Return the first known area keyword in a device name."""
    for keyword, area_name in _AREA_KEYWORDS.items():
        if keyword in device_name:
            return area_name
    return None


def _is_yeelight_device(device: dr.DeviceEntry) -> bool:
    """Return true when a HA device registry entry belongs to this integration."""
    return any(identifier[0] == DOMAIN for identifier in device.identifiers)
