"""Home Assistant device-registry helpers for Yeelight Pro."""

from __future__ import annotations

import inspect
import logging
from typing import Any, Mapping, Protocol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from .const import DOMAIN
from .device_display import registry_model_value
from .ha_house_registry import sync_house_device
from .house_metadata import house_device_info
from .ha_device_registry_source import (
    source_device_id_from_unique_id,
    source_device_ids as payload_source_device_ids,
)

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
    area_registry = ar.async_get(hass)
    synced_gateways = 0
    synced_devices = 0
    source_device_ids: dict[str, str] = {}
    should_resave_registry = not _method_supports(
        device_registry.async_get_or_create,
        "model_id",
    )

    _sync_house_device(device_registry, entry, coordinator)

    def _sync_device(device_payload: Mapping[str, Any], *, is_gateway: bool) -> bool:
        device_info = _device_info_from_payload(device_payload)
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
            "name",
            "serial_number",
            "sw_version",
            "hw_version",
            "configuration_url",
        ):
            value = device_info.get(key)
            if key == "model":
                value = registry_model_value(device_info, value)
            if value is not None:
                kwargs[key] = value
        if _method_supports(device_registry.async_get_or_create, "model_id"):
            model_id = _public_model_id(device_info.get("model_id"))
            if model_id is not None:
                kwargs["model_id"] = model_id

        device_entry = device_registry.async_get_or_create(**kwargs)
        device_entry = _sync_existing_device_metadata(
            device_registry,
            device_entry,
            device_info=device_info,
            identifiers=identifiers,
            connections=connections,
        )
        device_entry = _sync_existing_area(
            device_registry,
            area_registry,
            device_entry,
            suggested_area=device_info.get("suggested_area"),
        )
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
        if not is_gateway:
            for source_device_id in payload_source_device_ids(device_payload, identifiers):
                source_device_ids[source_device_id] = device_entry.id
        return True

    for gateway in coordinator.get_gateway_devices().values():
        if _sync_device(gateway, is_gateway=True):
            synced_gateways += 1

    for device in coordinator.data.values():
        if device.get("is_gateway"):
            continue
        if _sync_device(device, is_gateway=False):
            synced_devices += 1

    relinked_entities = _sync_entity_device_links(
        hass,
        entry,
        source_device_ids=source_device_ids,
    )

    if synced_gateways or synced_devices or relinked_entities:
        _LOGGER.info(
            "Synced %s gateway devices, %s source devices and %s entity links "
            "into HA registry",
            synced_gateways,
            synced_devices,
            relinked_entities,
        )
    if should_resave_registry:
        device_registry.async_schedule_save()


def active_device_identifiers(
    coordinator: DeviceRegistryCoordinator,
) -> set[tuple[str, str]]:
    """Return Yeelight Pro identifiers currently owned by a coordinator."""
    identifiers: set[tuple[str, str]] = set()

    if coordinator.house_id is not None:
        identifiers.update(normalize_registry_pairs(
            house_device_info(coordinator).get("identifiers")
        ))

    for device_payload in coordinator.get_gateway_devices().values():
        identifiers.update(device_payload_identifiers(device_payload))

    for device_payload in coordinator.data.values():
        identifiers.update(device_payload_identifiers(device_payload))

    return identifiers


def _sync_house_device(
    device_registry: dr.DeviceRegistry,
    entry: ConfigEntry,
    coordinator: DeviceRegistryCoordinator,
) -> None:
    """Keep house-level helper entities off legacy placeholder device names."""
    sync_house_device(
        device_registry,
        entry,
        coordinator,
        normalize_registry_pairs=normalize_registry_pairs,
        sync_metadata=_sync_existing_device_metadata,
    )


def device_payload_identifiers(
    device_payload: Mapping[str, Any],
) -> set[tuple[str, str]]:
    """Extract HA device identifiers from a normalized Yeelight payload."""
    device_info = _device_info_from_payload(device_payload)
    if not isinstance(device_info, Mapping):
        return set()
    return {
        identifier
        for identifier in normalize_registry_pairs(device_info.get("identifiers"))
        if identifier[0] == DOMAIN
    }


def _sync_existing_area(
    device_registry: dr.DeviceRegistry,
    area_registry: ar.AreaRegistry,
    device_entry: dr.DeviceEntry,
    *,
    suggested_area: Any,
) -> dr.DeviceEntry:
    """Set area_id from Yeelight room metadata without overriding user choice."""
    if getattr(device_entry, "area_id", None):
        return device_entry

    area_name = str(suggested_area).strip() if suggested_area is not None else ""
    if not area_name:
        return device_entry

    area = area_registry.async_get_area_by_name(area_name)
    if area is None:
        area = area_registry.async_create(area_name)

    updated = device_registry.async_update_device(device_entry.id, area_id=area.id)
    return updated or device_entry


def _device_info_from_payload(device_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return HA device_info from canonical instance or metadata-only fallback."""
    payload = device_payload.get("ha_device_instance")
    device_info = payload.get("device_info") if isinstance(payload, Mapping) else None
    if isinstance(device_info, Mapping):
        return _device_info_with_classification_context(device_info, device_payload)
    fallback = device_payload.get("device_info")
    if isinstance(fallback, Mapping):
        return _device_info_with_classification_context(fallback, device_payload)
    return None


def _device_info_with_classification_context(
    device_info: Mapping[str, Any],
    device_payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Add parent category evidence for local model normalization only."""
    context: dict[str, Any] = {}
    for key in ("iot_category", "category", "type"):
        if key not in device_info and key in device_payload:
            context[key] = device_payload[key]
    return dict(device_info, **context) if context else device_info


def _sync_existing_device_metadata(
    device_registry: dr.DeviceRegistry,
    device_entry: dr.DeviceEntry,
    *,
    device_info: Mapping[str, Any],
    identifiers: set[tuple[str, str]],
    connections: set[tuple[str, str]],
) -> dr.DeviceEntry:
    """Update metadata on existing devices without touching user-owned fields."""
    kwargs: dict[str, Any] = {}
    for source_key, target_key in (
        ("manufacturer", "manufacturer"),
        ("model", "model"),
        ("name", "name"),
        ("serial_number", "serial_number"),
        ("sw_version", "sw_version"),
        ("hw_version", "hw_version"),
        ("configuration_url", "configuration_url"),
    ):
        value = (
            registry_model_value(device_info, getattr(device_entry, target_key, None))
            if source_key == "model"
            else device_info.get(source_key)
        )
        if value is not None and getattr(device_entry, target_key, None) != value:
            kwargs[target_key] = value

    if _method_supports(device_registry.async_update_device, "model_id"):
        current_model_id = getattr(device_entry, "model_id", None)
        model_id = _public_model_id(device_info.get("model_id"))
        if model_id is not None and current_model_id != model_id:
            kwargs["model_id"] = model_id
        elif model_id is None and _is_internal_runtime_model_id(current_model_id):
            kwargs["model_id"] = None

    missing_identifiers = identifiers - set(getattr(device_entry, "identifiers", set()))
    if missing_identifiers:
        kwargs["merge_identifiers"] = missing_identifiers

    missing_connections = connections - set(getattr(device_entry, "connections", set()))
    if missing_connections:
        kwargs["merge_connections"] = missing_connections

    if not kwargs:
        return device_entry
    updated = device_registry.async_update_device(device_entry.id, **kwargs)
    return updated or device_entry


def _sync_entity_device_links(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    source_device_ids: Mapping[str, str],
) -> int:
    """Relink existing device-backed entities to their HA device entries."""
    if not source_device_ids:
        return 0

    entity_registry = er.async_get(hass)
    updated_count = 0
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry,
        entry.entry_id,
    ):
        if registry_entry.platform != DOMAIN or getattr(registry_entry, "device_id", None):
            continue
        source_device_id = source_device_id_from_unique_id(registry_entry.unique_id)
        if source_device_id is None:
            continue
        ha_device_id = source_device_ids.get(source_device_id)
        if ha_device_id is None:
            continue
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            device_id=ha_device_id,
        )
        updated_count += 1
    return updated_count


def _method_supports(method: Any, parameter_name: str) -> bool:
    """Return whether a HA registry method supports a keyword parameter."""
    try:
        return parameter_name in inspect.signature(method).parameters
    except (TypeError, ValueError):
        return False


def _public_model_id(value: Any) -> str | None:
    """Return a user-facing model_id, hiding internal runtime fallback ids."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or _is_internal_runtime_model_id(text):
        return None
    return text


def _is_internal_runtime_model_id(value: Any) -> bool:
    """Return true for historical runtime-* implementation detail model ids."""
    return isinstance(value, str) and value.startswith("runtime-")
