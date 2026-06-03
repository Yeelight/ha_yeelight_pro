"""Yeelight Pro Integration for Home Assistant.

支持 Yeelight Pro 云端和私有部署两种模式。
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import (
    area_registry as ar,
    config_validation as cv,
    device_registry as dr,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    CONF_ACCESS_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_CLOUD_DOMAIN,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_CLOUD,
    DEVICE_EVENT_TYPE,
    DOMAIN,
    PLATFORMS,
)
from .core.client import YeelightProClient
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import ConnectionError
from .entity_lifecycle import async_reconcile_entity_registry

_LOGGER = logging.getLogger(__name__)

# 服务 schema 定义
SERVICE_ASSIGN_AREAS_SCHEMA = vol.Schema({
    vol.Required("devices"): cv.ensure_list,
    vol.Required("area_id"): cv.string,
})

SERVICE_AUTO_ASSIGN_AREAS_SCHEMA = vol.Schema({
    vol.Optional("gateway_id"): cv.string,
})

SERVICE_DEBUG_EMIT_EVENT_SCHEMA = vol.Schema({
    vol.Required(ATTR_SOURCE_DEVICE_ID): vol.Any(int, cv.string),
    vol.Required(ATTR_COMPONENT_ID): cv.string,
    vol.Required(ATTR_EVENT_TYPE): cv.string,
    vol.Optional(ATTR_EVENT_ATTRIBUTES, default={}): dict,
})


def _build_debug_event_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    """将调试服务输入规范化为运行时事件总线载荷。"""
    return {
        ATTR_SOURCE_DEVICE_ID: str(data[ATTR_SOURCE_DEVICE_ID]),
        ATTR_COMPONENT_ID: str(data[ATTR_COMPONENT_ID]),
        ATTR_EVENT_TYPE: str(data[ATTR_EVENT_TYPE]),
        ATTR_EVENT_ATTRIBUTES: dict(data.get(ATTR_EVENT_ATTRIBUTES) or {}),
    }


def _normalize_registry_pairs(value: Any) -> set[tuple[str, str]]:
    """将 JSON 风格的配对数组转换为 HA 注册表元组集合。"""
    pairs: set[tuple[str, str]] = set()
    for item in value or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            pairs.add((str(item[0]), str(item[1])))
    return pairs


def _normalize_registry_pair(value: Any) -> tuple[str, str] | None:
    """将 JSON 风格的配对转换为 HA 注册表元组。"""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (str(value[0]), str(value[1]))
    return None


async def _async_sync_gateway_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
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

        identifiers = _normalize_registry_pairs(device_info.get("identifiers"))
        connections = _normalize_registry_pairs(device_info.get("connections"))
        if not identifiers and not connections:
            return False

        kwargs: dict[str, Any] = {
            "config_entry_id": entry.entry_id,
            "identifiers": identifiers,
        }
        if connections:
            kwargs["connections"] = connections

        via_device = _normalize_registry_pair(device_info.get("via_device"))
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


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Yeelight Pro integration."""
    hass.data.setdefault(DOMAIN, {})

    # 注册批量分配区域服务
    async def handle_assign_areas(call: ServiceCall) -> None:
        """处理批量分配区域服务。"""
        devices = call.data["devices"]
        area_id = call.data["area_id"]
        device_registry = dr.async_get(hass)

        for device_id in devices:
            try:
                device_registry.async_update_device(device_id, area_id=area_id)
                _LOGGER.info("Assigned device %s to area %s", device_id, area_id)
            except Exception as err:
                _LOGGER.error("Failed to assign device %s: %s", device_id, err)

    # 注册自动分配区域服务
    async def handle_auto_assign_areas(call: ServiceCall) -> None:
        """处理自动分配区域服务。"""
        gateway_id = call.data.get("gateway_id")
        device_registry = dr.async_get(hass)
        area_registry = ar.async_get(hass)

        area_map = {area.name: area.id for area in area_registry.async_list_areas()}

        # 房间关键词映射
        area_keywords = {
            "客厅": "客厅", "卧室": "卧室", "主卧": "主卧",
            "次卧": "次卧", "厨房": "厨房", "餐厅": "餐厅",
            "书房": "书房", "阳台": "阳台", "卫生间": "卫生间",
            "浴室": "浴室", "走廊": "走廊", "玄关": "玄关",
            "工作区": "工作区",
        }

        assigned_count = 0
        for device in device_registry.devices.values():
            if gateway_id and device.id != gateway_id:
                continue

            # 过滤 Yeelight Pro 设备
            if not any(identifier[0] == DOMAIN for identifier in device.identifiers):
                continue

            device_name = device.name or ""
            for keyword, area_name in area_keywords.items():
                if keyword in device_name:
                    if area_name not in area_map:
                        new_area = area_registry.async_create(area_name)
                        area_map[area_name] = new_area.id
                        _LOGGER.info("Created new area: %s", area_name)

                    device_registry.async_update_device(
                        device.id,
                        area_id=area_map[area_name],
                    )
                    assigned_count += 1
                    _LOGGER.info("Auto-assigned %s to %s", device_name, area_name)
                    break

        _LOGGER.info("Auto-assigned %s devices to areas", assigned_count)

    # 注册调试事件发射服务
    async def handle_debug_emit_event(call: ServiceCall) -> None:
        """向 HA 事件总线发射调试 Yeelight Pro 设备事件。"""
        payload = _build_debug_event_payload(call.data)
        hass.bus.async_fire(DEVICE_EVENT_TYPE, payload)
        _LOGGER.info(
            "Emitted debug Yeelight Pro event: source_device_id=%s "
            "component_id=%s event_type=%s",
            payload[ATTR_SOURCE_DEVICE_ID],
            payload[ATTR_COMPONENT_ID],
            payload[ATTR_EVENT_TYPE],
        )

    hass.services.async_register(
        DOMAIN, "assign_areas", handle_assign_areas,
        schema=SERVICE_ASSIGN_AREAS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "auto_assign_areas", handle_auto_assign_areas,
        schema=SERVICE_AUTO_ASSIGN_AREAS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "debug_emit_event", handle_debug_emit_event,
        schema=SERVICE_DEBUG_EMIT_EVENT_SCHEMA,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yeelight Pro from a config entry."""
    # 获取配置
    connection_mode = entry.data[CONF_CONNECTION_MODE]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    house_id = entry.data[CONF_HOUSE_ID]

    # 确定域名
    if connection_mode == CONNECTION_MODE_CLOUD:
        domain = entry.data.get(CONF_CLOUD_DOMAIN, "api.yeelight.com")
    else:
        domain = entry.data.get(CONF_PRIVATE_DOMAIN, "192.168.1.100:8080")

    # 创建客户端
    session = async_get_clientsession(hass)
    client = YeelightProClient(
        domain=domain,
        access_token=access_token,
        session=session,
    )

    # 验证服务可达性（仅检查连通性，token 在 config_flow 已验证）
    try:
        await client.check_health()
    except ConnectionError as err:
        raise ConfigEntryNotReady(f"Connection failed: {err}") from err

    # 创建协调器
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=client,
        house_id=house_id,
    )

    # 首次数据更新
    await coordinator.async_config_entry_first_refresh()

    # 同步网关设备到 HA 注册表
    await _async_sync_gateway_devices(hass, entry, coordinator)

    # 清理过期实体注册表条目
    await async_reconcile_entity_registry(hass, entry, coordinator)

    # 存储到 hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    # 拓扑变更监听：自动触发设备同步和实体清理
    last_topology_generation = coordinator.topology_generation

    def _schedule_topology_sync() -> None:
        nonlocal last_topology_generation
        if coordinator.topology_generation == last_topology_generation:
            return
        last_topology_generation = coordinator.topology_generation
        hass.async_create_task(_async_sync_gateway_devices(hass, entry, coordinator))
        hass.async_create_task(async_reconcile_entity_registry(hass, entry, coordinator))

    entry.async_on_unload(coordinator.async_add_listener(_schedule_topology_sync))

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "Yeelight Pro integration setup complete for house %s (%s mode)",
        house_id,
        connection_mode,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["client"].disconnect()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
