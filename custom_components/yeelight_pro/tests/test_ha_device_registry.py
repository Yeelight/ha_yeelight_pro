"""Home Assistant device-registry synchronization tests."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.ha_device_registry import (
    async_sync_gateway_devices,
)


class _Coordinator:
    data: Mapping[Any, Mapping[str, Any]]
    house_id: int | None

    def __init__(
        self,
        data: Mapping[Any, Mapping[str, Any]],
        gateways: Mapping[Any, Mapping[str, Any]] | None = None,
    ) -> None:
        self.data = data
        self.house_id = 12345
        self._gateways = gateways or {}

    def get_gateway_devices(self) -> Mapping[Any, Mapping[str, Any]]:
        return dict(self._gateways)


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, entry_id="entry-1")


def _device_payload(
    *,
    identifier: str,
    name: str = "客厅主灯",
    model: str = "智能筒灯",
    suggested_area: str = "客厅",
) -> dict:
    return {
        "ha_device_instance": {
            "device_info": {
                "identifiers": [[DOMAIN, identifier]],
                "manufacturer": "Yeelight",
                "model": model,
                "model_id": "YL-100",
                "name": name,
                "suggested_area": suggested_area,
            }
        }
    }


def _fallback_device_payload(
    *,
    identifier: str,
    name: str = "墙壁开关1",
    model: str = "relay_switch",
    suggested_area: str = "客厅",
) -> dict:
    return {
        "device_info": {
            "identifiers": [[DOMAIN, identifier], [DOMAIN, f"device:{identifier}"]],
            "manufacturer": "Yeelight",
            "model": model,
            "model_id": "YL-201",
            "name": name,
            "suggested_area": suggested_area,
        },
        "device_id": int(identifier),
    }


async def test_sync_gateway_devices_sets_area_id_from_existing_suggested_area(
    hass: HomeAssistant,
) -> None:
    """同步 registry 时应把已有同名 HA 区域写入空白设备 area_id."""
    entry = _entry()
    entry.add_to_hass(hass)
    area = ar.async_get(hass).async_create("客厅")
    coordinator = _Coordinator({"device-1": _device_payload(identifier="387958")})

    await async_sync_gateway_devices(hass, entry, coordinator)

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "387958")})
    assert device is not None
    assert device.name == "客厅主灯"
    assert device.model == "智能筒灯"
    assert device.area_id == area.id


async def test_sync_gateway_devices_creates_area_from_source_room_name(
    hass: HomeAssistant,
) -> None:
    """有明确 Yeelight 房间名时应创建 HA area，避免集成设备页房间为空."""
    entry = _entry()
    entry.add_to_hass(hass)
    area_registry = ar.async_get(hass)
    coordinator = _Coordinator({"device-1": _device_payload(identifier="387958")})

    await async_sync_gateway_devices(hass, entry, coordinator)

    area = area_registry.async_get_area_by_name("客厅")
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "387958")})
    assert area is not None
    assert device is not None
    assert device.area_id == area.id


async def test_sync_gateway_devices_does_not_override_user_area(
    hass: HomeAssistant,
) -> None:
    """已有用户区域不应被 suggested_area 覆盖。"""
    entry = _entry()
    entry.add_to_hass(hass)
    user_area = ar.async_get(hass).async_create("卧室")
    ar.async_get(hass).async_create("客厅")
    device_registry = dr.async_get(hass)
    existing = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "387958")},
        name="旧名称",
    )
    device_registry.async_update_device(existing.id, area_id=user_area.id)
    coordinator = _Coordinator({"device-1": _device_payload(identifier="387958")})

    await async_sync_gateway_devices(hass, entry, coordinator)

    device = device_registry.async_get(existing.id)
    assert device is not None
    assert device.area_id == user_area.id


async def test_sync_gateway_devices_uses_metadata_only_fallback_device_info(
    hass: HomeAssistant,
) -> None:
    """无 ha_device_instance 时也应把设备 metadata 同步到 HA registry."""
    entry = _entry()
    entry.add_to_hass(hass)
    area = ar.async_get(hass).async_create("客厅")
    coordinator = _Coordinator(
        {"device-1": _fallback_device_payload(identifier="304784336")}
    )

    await async_sync_gateway_devices(hass, entry, coordinator)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, "304784336")}
    )
    assert device is not None
    assert device.name == "墙壁开关1"
    assert device.model == "relay_switch"
    assert device.area_id == area.id


async def test_sync_gateway_devices_relinks_existing_device_entities(
    hass: HomeAssistant,
) -> None:
    """已有游离实体应按 unique_id 回填到对应 HA device_id."""
    entry = _entry()
    entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get_or_create(
        "switch",
        DOMAIN,
        "yeelight_pro_304784336_switch",
        config_entry=entry,
    )
    assert entity_entry.device_id is None
    coordinator = _Coordinator(
        {"device-1": _fallback_device_payload(identifier="304784336")}
    )

    await async_sync_gateway_devices(hass, entry, coordinator)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, "304784336")}
    )
    updated_entity = entity_registry.async_get(entity_entry.entity_id)
    assert device is not None
    assert updated_entity is not None
    assert updated_entity.device_id == device.id
