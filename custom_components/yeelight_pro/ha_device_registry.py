"""Home Assistant device-registry helpers for Yeelight Pro."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Protocol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DeviceRegistryCoordinator(Protocol):
    """Device registry helpers need only the topology-facing coordinator shape."""

    data: Mapping[Any, Mapping[str, Any]]
    house_id: int | None

    def get_gateway_devices(self) -> Mapping[Any, Mapping[str, Any]]:
        """Return normalized gateway payloads for registry topology."""


def normalize_registry_pairs(value: Any) -> set[tuple[str, str]]:
    """将 JSON 风格的配对数组转换为 HA 注册表元组集合。"""
    pairs: set[tuple[str, str]] = set()
    for item in value or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            pairs.add((str(item[0]), str(item[1])))
    return pairs


def normalize_registry_pair(value: Any) -> tuple[str, str] | None:
    """将 JSON 风格的配对转换为 HA 注册表元组。"""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (str(value[0]), str(value[1]))
    return None


async def async_sync_gateway_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: DeviceRegistryCoordinator,
) -> None:
    """确保网关父设备和源设备存在于 HA 设备注册表中。"""
    device_registry = dr.async_get(hass)
    synced_gateways = 0
    synced_devices = 0

    def _sync_device(device_payload: Mapping[str, Any], *, is_gateway: bool) -> bool:
        payload = device_payload.get("ha_device_instance")
        device_info = payload.get("device_info") if isinstance(payload, Mapping) else None
        if not isinstance(device_info, Mapping):
            return False

        identifiers = normalize_registry_pairs(device_info.get("identifiers"))
        connections = normalize_registry_pairs(device_info.get("connections"))
        if not identifiers and not connections:
            return False

        kwargs: dict[str, Any] = {
            "config_entry_id": entry.entry_id,
            "identifiers": identifiers,
        }
        if connections:
            kwargs["connections"] = connections

        via_device = normalize_registry_pair(device_info.get("via_device"))
        if via_device is not None:
            kwargs["via_device"] = via_device

        for key in (
            "manufacturer",
            "model",
            "model_id",
            "name",
            "serial_number",
            "sw_version",
            "hw_version",
            "configuration_url",
            "suggested_area",
        ):
            value = device_info.get(key)
            if value is not None:
                kwargs[key] = value

        device_entry = device_registry.async_get_or_create(**kwargs)
        if via_device is not None:
            parent_entry = device_registry.async_get_device(identifiers={via_device})
            if (
                parent_entry is not None
                and getattr(device_entry, "via_device_id", None) != parent_entry.id
            ):
                updated = device_registry.async_update_device(
                    device_entry.id,
                    via_device_id=parent_entry.id,
                )
                if updated is not None:
                    device_entry = updated
        _LOGGER.debug(
            "Synced %s device %s into HA registry as %s with identifiers=%s",
            "gateway" if is_gateway else "source",
            kwargs.get("name"),
            getattr(device_entry, "id", None),
            sorted(identifiers),
        )
        return True

    for gateway in coordinator.get_gateway_devices().values():
        if _sync_device(gateway, is_gateway=True):
            synced_gateways += 1

    for device in coordinator.data.values():
        if device.get("is_gateway"):
            continue
        if _sync_device(device, is_gateway=False):
            synced_devices += 1

    if synced_gateways or synced_devices:
        _LOGGER.info(
            "Synced %s gateway devices and %s source devices into HA registry",
            synced_gateways,
            synced_devices,
        )


def active_device_identifiers(
    coordinator: DeviceRegistryCoordinator,
) -> set[tuple[str, str]]:
    """Return Yeelight Pro identifiers currently owned by a coordinator."""
    identifiers: set[tuple[str, str]] = set()

    if coordinator.house_id is not None:
        identifiers.add((DOMAIN, str(coordinator.house_id)))

    for device_payload in coordinator.get_gateway_devices().values():
        identifiers.update(device_payload_identifiers(device_payload))

    for device_payload in coordinator.data.values():
        identifiers.update(device_payload_identifiers(device_payload))

    return identifiers


def device_payload_identifiers(
    device_payload: Mapping[str, Any],
) -> set[tuple[str, str]]:
    """Extract HA device identifiers from a normalized Yeelight payload."""
    payload = device_payload.get("ha_device_instance")
    device_info = payload.get("device_info") if isinstance(payload, Mapping) else None
    if not isinstance(device_info, Mapping):
        return set()
    return {
        identifier
        for identifier in normalize_registry_pairs(device_info.get("identifiers"))
        if identifier[0] == DOMAIN
    }
