"""Pure adapters for received Yeelight Pro LAN gateway payloads."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
)
from .event_support import (
    SENSITIVE_RUNTIME_EVENT_PARAM_KEYS,
    safe_runtime_event_params,
)
from .lan_methods import METHOD_POST_EVENT, METHOD_POST_PROP
from .utils import to_int

_SENSITIVE_EVENT_PARAM_KEYS = SENSITIVE_RUNTIME_EVENT_PARAM_KEYS


@dataclass(frozen=True, slots=True)
class YeelightLanPropertyUpdate:
    """LAN 状态推送归一化后的属性更新。"""

    node_id: int
    node_type: int | None
    params: dict[str, Any]


def lan_property_updates(
    message: Mapping[str, Any],
) -> list[YeelightLanPropertyUpdate]:
    """将 ``gateway_post.prop`` 帧转换为本地状态更新。"""
    if message.get("method") != METHOD_POST_PROP:
        return []

    updates: list[YeelightLanPropertyUpdate] = []
    for node in _iter_nodes(message):
        node_id = to_int(node.get("id"))
        if node_id is None:
            continue

        params = _node_params(node)
        online = node.get("o")
        if isinstance(online, bool):
            params["o"] = online
        elif not params:
            raise HomeAssistantError("Invalid Yeelight Pro LAN property node params")

        if params:
            updates.append(
                YeelightLanPropertyUpdate(
                    node_id=node_id,
                    node_type=to_int(node.get("nt")),
                    params=params,
                )
            )
    return updates


def lan_event_payloads(message: Mapping[str, Any]) -> list[dict[str, Any]]:
    """将 ``gateway_post.event`` 节点转换为运行时事件入口格式。"""
    if message.get("method") != METHOD_POST_EVENT:
        return []

    events: list[dict[str, Any]] = []
    message_meta = _message_meta(message)
    for node in _iter_nodes(message):
        node_id = to_int(node.get("id"))
        event_type = node.get("value")
        if node_id is None or event_type in (None, ""):
            continue

        attributes = dict(message_meta)
        node_type = to_int(node.get("nt"))
        if node_type is not None:
            attributes["node_type"] = node_type
        params = node.get("params")
        if isinstance(params, Mapping) and params:
            safe_params = _safe_event_params(params)
            if safe_params:
                attributes["params"] = safe_params
        attributes["raw_event"] = event_type

        events.append(
            {
                ATTR_SOURCE_DEVICE_ID: str(node_id),
                ATTR_COMPONENT_ID: _component_id(node),
                ATTR_EVENT_TYPE: event_type,
                ATTR_EVENT_ATTRIBUTES: attributes,
            }
        )
    return events


def _iter_nodes(message: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """返回 LAN gateway_post 帧中的合法节点。"""
    nodes = message.get("nodes")
    if not isinstance(nodes, list):
        raise HomeAssistantError("Invalid Yeelight Pro LAN payload nodes")
    if not all(isinstance(node, Mapping) for node in nodes):
        raise HomeAssistantError("Invalid Yeelight Pro LAN payload node")
    return list(nodes)


def _node_params(node: Mapping[str, Any]) -> dict[str, Any]:
    """返回可安全合并进状态的节点属性。"""
    params = node.get("params")
    if not isinstance(params, Mapping):
        if params is None and isinstance(node.get("o"), bool):
            return {}
        raise HomeAssistantError("Invalid Yeelight Pro LAN property node params")
    return dict(params)


def _message_meta(message: Mapping[str, Any]) -> dict[str, Any]:
    """返回可写入事件 attributes 的脱敏 LAN 消息元数据。"""
    meta: dict[str, Any] = {"method": METHOD_POST_EVENT}
    message_id = message.get("id")
    version = message.get("version")
    if message_id not in (None, ""):
        meta["message_id"] = str(message_id)
    if version not in (None, ""):
        meta["version"] = str(version)
    return meta


def _component_id(node: Mapping[str, Any]) -> str:
    """返回 LAN 节点事件的稳定 fallback component_id。"""
    component_id = node.get("componentId") or node.get("component_id")
    if component_id not in (None, ""):
        return str(component_id)
    node_type = to_int(node.get("nt"))
    if node_type is not None:
        return f"node_type_{node_type}"
    return "lan_event"


def _safe_event_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """保留自动化所需事件参数，同时过滤凭据和设备标识。"""
    return safe_runtime_event_params(params)


__all__ = [
    "YeelightLanPropertyUpdate",
    "lan_event_payloads",
    "lan_property_updates",
]
