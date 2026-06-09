"""Yeelight Pro 设备触发器.

为 Yeelight Pro 事件型设备提供 Home Assistant device trigger 支持，
使自动化可以基于按钮点击、旋钮旋转等事件触发。
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import (
    DEVICE_TRIGGER_BASE_SCHEMA,
    InvalidDeviceAutomationConfig,
)
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_COMPONENT_ID, ATTR_EVENT_TYPE, ATTR_SOURCE_DEVICE_ID, DEVICE_EVENT_TYPE, DOMAIN
from .projector.event import HADeviceTriggerProjection, project_device_triggers

CONF_SUBTYPE = "subtype"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): str, vol.Required(CONF_SUBTYPE): str}
)


async def async_validate_trigger_config(
    hass: HomeAssistant,
    config: ConfigType,
) -> ConfigType:
    """验证设备触发器配置."""
    config = TRIGGER_SCHEMA(config)
    triggers = await async_get_triggers(hass, config[CONF_DEVICE_ID])
    supported = {
        (trigger[CONF_TYPE], trigger[CONF_SUBTYPE])
        for trigger in triggers
    }
    requested = (config[CONF_TYPE], config[CONF_SUBTYPE])
    if requested not in supported:
        raise InvalidDeviceAutomationConfig(
            f"device does not support trigger {requested}"
        )
    return config


async def async_get_triggers(
    hass: HomeAssistant,
    device_id: str,
) -> list[dict[str, str]]:
    """列出 Yeelight Pro 设备支持的触发器."""
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(device_id)
    if device_entry is None:
        return []

    source_device_id = _source_device_id(device_entry)
    if source_device_id is None:
        return []

    triggers = _device_trigger_projections(hass, device_entry, source_device_id)
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: trigger.type,
            CONF_SUBTYPE: trigger.subtype,
        }
        for trigger in triggers
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """附加设备触发器."""
    config = await async_validate_trigger_config(hass, config)
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(config[CONF_DEVICE_ID])
    if device_entry is None:
        raise InvalidDeviceAutomationConfig("device not found")

    source_device_id = _source_device_id(device_entry)
    if source_device_id is None:
        raise InvalidDeviceAutomationConfig("device is not a Yeelight Pro source device")

    trigger_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: DEVICE_EVENT_TYPE,
            event_trigger.CONF_EVENT_DATA: {
                ATTR_SOURCE_DEVICE_ID: source_device_id,
                ATTR_COMPONENT_ID: config[CONF_TYPE],
                ATTR_EVENT_TYPE: config[CONF_SUBTYPE],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass,
        trigger_config,
        action,
        trigger_info,
        platform_type="device",
    )


def _source_device_id(device_entry: dr.DeviceEntry) -> str | None:
    """从设备标识符中提取源设备 ID."""
    for domain, identifier in device_entry.identifiers:
        if domain != DOMAIN:
            continue
        text = str(identifier)
        if text.startswith("device:"):
            return text.removeprefix("device:")
    return None


def _device_trigger_projections(
    hass: HomeAssistant,
    device_entry: dr.DeviceEntry,
    source_device_id: str,
) -> list[HADeviceTriggerProjection]:
    """获取设备触发器投影列表."""
    for entry_id in device_entry.config_entries:
        runtime_entry = hass.data.get(DOMAIN, {}).get(entry_id)
        if not isinstance(runtime_entry, dict):
            continue
        coordinator = runtime_entry.get("coordinator")
        if coordinator is None:
            continue
        device_payload = coordinator.get_device(_coerce_source_device_id(source_device_id))
        if device_payload:
            return project_device_triggers(device_payload)
    return []


def _coerce_source_device_id(source_device_id: str) -> Any:
    """将字符串设备 ID 转换为整数类型（如可能）."""
    try:
        return int(source_device_id)
    except (TypeError, ValueError):
        return source_device_id
