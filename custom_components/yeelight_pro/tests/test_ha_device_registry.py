"""Home Assistant device-registry synchronization tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.ha_device_registry import async_sync_gateway_devices

from .ha_device_registry_helpers import (
    DeviceRegistryCoordinator,
    device_payload,
    fallback_device_payload,
)


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, entry_id="entry-1")


async def test_sync_gateway_devices_sets_area_id_from_existing_suggested_area(
    hass: HomeAssistant,
) -> None:
    """同步 registry 时应把已有同名 HA 区域写入空白设备 area_id."""
    entry = _entry()
    entry.add_to_hass(hass)
    area = ar.async_get(hass).async_create("客厅")
    coordinator = DeviceRegistryCoordinator({
        "device-1": device_payload(identifier="387958")
    })

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
    coordinator = DeviceRegistryCoordinator({
        "device-1": device_payload(identifier="387958")
    })

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
    coordinator = DeviceRegistryCoordinator({
        "device-1": device_payload(identifier="387958")
    })

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
    coordinator = DeviceRegistryCoordinator(
        {"device-1": fallback_device_payload(identifier="304784336")}
    )

    await async_sync_gateway_devices(hass, entry, coordinator)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, "304784336")}
    )
    assert device is not None
    assert device.name == "墙壁开关1"
    assert device.model == "墙壁开关"
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
    coordinator = DeviceRegistryCoordinator(
        {"device-1": fallback_device_payload(identifier="304784336")}
    )

    await async_sync_gateway_devices(hass, entry, coordinator)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, "304784336")}
    )
    updated_entity = entity_registry.async_get(entity_entry.entity_id)
    assert device is not None
    assert updated_entity is not None
    assert updated_entity.device_id == device.id


async def test_sync_gateway_devices_updates_legacy_house_placeholder_devices(
    hass: HomeAssistant,
) -> None:
    """旧家庭壳设备不能继续显示 Yeelight Pro/House 加 id 的占位名."""
    entry = _entry()
    entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    legacy = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "12345")},
        manufacturer="Yeelight",
        name="Yeelight Pro 12345",
    )
    device_registry.async_update_device(legacy.id, name_by_user="House 12345")
    coordinator = DeviceRegistryCoordinator({})

    await async_sync_gateway_devices(hass, entry, coordinator)

    updated = device_registry.async_get(legacy.id)
    assert updated is not None
    assert updated.name == "绿地中央公园"
    assert updated.name_by_user is None
    assert updated.model == "Yeelight Pro 家庭"
    assert (DOMAIN, "12345") in updated.identifiers
    assert (DOMAIN, "house:12345") in updated.identifiers


async def test_sync_gateway_devices_schedules_save_to_drop_legacy_unknown_fields(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """当前 HA 不支持 model_id 时，应重写 registry 以丢弃旧未知字段."""
    entry = _entry()
    entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    save_calls = 0

    def _record_save() -> None:
        nonlocal save_calls
        save_calls += 1

    monkeypatch.setattr(device_registry, "async_schedule_save", _record_save)
    coordinator = DeviceRegistryCoordinator(
        {"device-1": fallback_device_payload(identifier="304784336")}
    )

    await async_sync_gateway_devices(hass, entry, coordinator)

    assert save_calls >= 1
