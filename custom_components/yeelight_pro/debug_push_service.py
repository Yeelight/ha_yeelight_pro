"""Debug push services for Yeelight Pro."""
from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import (
    ATTR_SOURCE_DEVICE_ID,
    CONF_DEVICE_IMPORT_FILTER,
    DOMAIN,
)
from .debug_runtime import ATTR_ENTRY_ID, debug_coordinator, debug_runtime_entry
from .debug_push_logging import (
    debug_push_emit_log_payload,
    push_health_log_payload,
)
from .device_filter import normalize_device_import_filter
from .diagnostic_runtime import push_manager_health
from .ha_device_registry_source import source_device_id_from_unique_id
from .push_transport_frames import private_subscribe_state_payload

_LOGGER = logging.getLogger(__name__)
ATTR_ENTITY_ID = "entity_id"
ATTR_NODE_TYPE = "node_type"
ATTR_PAYLOAD_SHAPE = "payload_shape"
ATTR_PARAMS = "params"
PAYLOAD_SHAPE_PROP = "prop"
PAYLOAD_SHAPE_PRIVATE_SUBSCRIBE_SNAPSHOT = "private_subscribe_snapshot"
SERVICE_DEBUG_DUMP_PUSH_HEALTH = "debug_dump_push_health"
SERVICE_DEBUG_EMIT_PUSH_PAYLOAD = "debug_emit_push_payload"

SERVICE_DEBUG_DUMP_PUSH_HEALTH_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
})
SERVICE_DEBUG_EMIT_PUSH_PAYLOAD_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Optional(ATTR_SOURCE_DEVICE_ID): vol.Any(int, cv.string),
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Optional(ATTR_NODE_TYPE, default=2): vol.Coerce(int),
    vol.Optional(ATTR_PAYLOAD_SHAPE, default=PAYLOAD_SHAPE_PROP): vol.In(
        (PAYLOAD_SHAPE_PROP, PAYLOAD_SHAPE_PRIVATE_SUBSCRIBE_SNAPSHOT)
    ),
    vol.Required(ATTR_PARAMS): dict,
})


def async_register_debug_push_services(hass: HomeAssistant) -> None:
    """Register guarded debug push services."""

    async def handle_debug_dump_push_health(call: ServiceCall) -> None:
        """向 HA 日志输出聚合后的 WebSocket 推送链路诊断。"""
        entry_id = call.data.get(ATTR_ENTRY_ID)
        runtime = debug_runtime_entry(hass, entry_id=entry_id)
        if runtime is None:
            raise HomeAssistantError("Yeelight Pro debug mode is disabled or entry_id is invalid")
        health = push_manager_health(
            runtime.get("push_manager"),
            import_filter_active=_debug_import_filter_active(runtime),
        )
        payload = push_health_log_payload(health)
        _LOGGER.info(
            "Yeelight Pro push health debug dump: %s",
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
        )

    async def handle_debug_emit_push_payload(call: ServiceCall) -> None:
        """注入一条合成属性推送，验证内部实时刷新链路。"""
        entry_id = call.data.get(ATTR_ENTRY_ID)
        coordinator = debug_coordinator(hass, entry_id=entry_id)
        if coordinator is None:
            raise HomeAssistantError("Yeelight Pro debug mode is disabled or entry_id is invalid")
        payload = _debug_push_payload(hass, call.data)
        await coordinator.async_handle_push_payload(payload)
        summary = getattr(coordinator, "last_push_property_summary", None)
        summary_dict = (
            summary.as_dict()
            if summary is not None and callable(getattr(summary, "as_dict", None))
            else {}
        )
        _LOGGER.info(
            "Emitted debug Yeelight Pro push payload: %s",
            json.dumps(
                debug_push_emit_log_payload(summary_dict),
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_DEBUG_DUMP_PUSH_HEALTH,
        handle_debug_dump_push_health,
        schema=SERVICE_DEBUG_DUMP_PUSH_HEALTH_SCHEMA,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
        handle_debug_emit_push_payload,
        schema=SERVICE_DEBUG_EMIT_PUSH_PAYLOAD_SCHEMA,
    )


def _debug_import_filter_active(runtime: Mapping[str, Any]) -> bool:
    """返回导入过滤是否启用，仅用于聚合诊断。"""
    entry = runtime.get("entry")
    options = getattr(entry, "options", None)
    if not isinstance(options, Mapping):
        return False
    return normalize_device_import_filter(
        options.get(CONF_DEVICE_IMPORT_FILTER),
    ).enabled


def _debug_push_payload(hass: HomeAssistant, data: Mapping[str, Any]) -> dict[str, Any]:
    """构造标准 prop 推送，不包含 token、URL 或真实服务端帧。"""
    source_device_id = _debug_source_device_id(hass, data)
    params = dict(data.get(ATTR_PARAMS) or {})
    if data.get(ATTR_PAYLOAD_SHAPE) == PAYLOAD_SHAPE_PRIVATE_SUBSCRIBE_SNAPSHOT:
        return _debug_private_subscribe_snapshot_payload(
            source_device_id=source_device_id,
            node_type=data.get(ATTR_NODE_TYPE),
            params=params,
        )
    return {
        "type": "prop",
        "nodes": [
            {
                "id": source_device_id,
                "nt": data.get(ATTR_NODE_TYPE),
                "params": params,
            }
        ],
    }


def _debug_private_subscribe_snapshot_payload(
    *,
    source_device_id: Any,
    node_type: Any,
    params: Mapping[str, Any],
) -> dict[str, Any]:
    """用生产私有帧转换逻辑模拟 subscribe snapshot 状态推送。"""
    raw_payload = {
        "result": "ok",
        "data": {
            "method": "subscribe",
            "devices": [
                {
                    "id": source_device_id,
                    "nt": node_type,
                    "params": dict(params),
                }
            ],
        },
    }
    payload = private_subscribe_state_payload(raw_payload)
    if payload is None:
        raise HomeAssistantError("debug private subscribe snapshot produced no state payload")
    return payload


def _debug_source_device_id(hass: HomeAssistant, data: Mapping[str, Any]) -> Any:
    """返回合成 push 的源设备 ID，可从 HA entity_id 解析。"""
    explicit = data.get(ATTR_SOURCE_DEVICE_ID)
    if explicit not in (None, ""):
        return explicit
    entity_id = data.get(ATTR_ENTITY_ID)
    if not isinstance(entity_id, str) or not entity_id:
        raise HomeAssistantError("source_device_id or entity_id is required")
    registry_entry = er.async_get(hass).async_get(entity_id)
    unique_id = getattr(registry_entry, "unique_id", None)
    if not isinstance(unique_id, str):
        raise HomeAssistantError("entity_id does not resolve to a Yeelight Pro entity")
    source_device_id = source_device_id_from_unique_id(unique_id)
    if source_device_id is None:
        raise HomeAssistantError("entity_id does not resolve to a Yeelight Pro device")
    return source_device_id
