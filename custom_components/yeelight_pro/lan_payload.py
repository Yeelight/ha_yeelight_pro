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
from .lan_methods import (
    METHOD_DEVICE_POST_EVENT,
    METHOD_DEVICE_POST_PROP,
    METHOD_DEVICE_POST_TOPOLOGY,
    METHOD_POST_EVENT,
    METHOD_POST_PROP,
    METHOD_POST_TOPOLOGY,
)
from .utils import to_int

_SENSITIVE_EVENT_PARAM_KEYS = SENSITIVE_RUNTIME_EVENT_PARAM_KEYS


@dataclass(frozen=True, slots=True)
class YeelightLanPropertyUpdate:
    """LAN 状态推送归一化后的属性更新。"""

    node_id: int
    node_type: int | None
    params: dict[str, Any]


_PROP_METHODS = {METHOD_POST_PROP, METHOD_DEVICE_POST_PROP}
_EVENT_METHODS = {METHOD_POST_EVENT, METHOD_DEVICE_POST_EVENT}
_TOPOLOGY_METHODS = {METHOD_POST_TOPOLOGY, METHOD_DEVICE_POST_TOPOLOGY}


def lan_property_updates(
    message: Mapping[str, Any],
) -> list[YeelightLanPropertyUpdate]:
    """将 ``gateway_post.prop`` 或 ``device_post.prop`` 帧转换为本地状态更新。"""
    if message.get("method") not in _PROP_METHODS:
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
    """将 ``gateway_post.event`` 或 ``device_post.event`` 节点转换为运行时事件入口格式。"""
    method = message.get("method")
    if method not in _EVENT_METHODS:
        return []

    # WiFi 全面屏事件格式（device_post.event）：顶层 params 包含 id/type/params
    if method == METHOD_DEVICE_POST_EVENT:
        return _lan_device_event_payloads(message)

    # 网关事件格式（gateway_post.event）：nodes 数组
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


def _lan_device_event_payloads(message: Mapping[str, Any]) -> list[dict[str, Any]]:
    """解析 WiFi 全面屏 ``device_post.event`` 事件。

    格式：{"method": "device_post.event", "id": 116,
           "params": {"id": 7919, "type": "keyClick", "params": {"key": 1, "count": 1}}}
    """
    top_params = message.get("params")
    if not isinstance(top_params, Mapping):
        return []
    node_id = to_int(top_params.get("id"))
    event_type = top_params.get("type")
    if node_id is None or event_type in (None, ""):
        return []

    attributes: dict[str, Any] = {"method": METHOD_DEVICE_POST_EVENT}
    message_id = message.get("id")
    if isinstance(message_id, int):
        attributes["message_id"] = str(message_id)

    inner_params = top_params.get("params")
    if isinstance(inner_params, Mapping) and inner_params:
        safe_params = _safe_event_params(inner_params)
        if safe_params:
            attributes["params"] = safe_params
    attributes["raw_event"] = event_type

    return [
        {
            ATTR_SOURCE_DEVICE_ID: str(node_id),
            ATTR_COMPONENT_ID: "wifi_panel",
            ATTR_EVENT_TYPE: event_type,
            ATTR_EVENT_ATTRIBUTES: attributes,
        }
    ]


@dataclass(frozen=True, slots=True)
class LanTopologyUpdate:
    """拓扑推送通知，表示网关拓扑发生了变更。"""

    message_id: int | None
    node_count: int


def lan_topology_update(message: Mapping[str, Any]) -> LanTopologyUpdate | None:
    """解析 ``gateway_post.topology`` 或 ``getway_post.topology`` 消息。

    网关在设备增删、分组变化、改名时会主动推送拓扑。
    返回 None 表示不是拓扑消息。
    """
    if message.get("method") not in _TOPOLOGY_METHODS:
        return None
    nodes = message.get("nodes")
    node_count = len(nodes) if isinstance(nodes, list) else 0
    return LanTopologyUpdate(
        message_id=to_int(message.get("id")),
        node_count=node_count,
    )


@dataclass(frozen=True, slots=True)
class LanSceneStateUpdate:
    """场景状态更新。"""

    scene_id: int
    name: str | None
    state: str  # "active", "inactive", "unknown"


def lan_scene_updates(
    message: Mapping[str, Any],
) -> list[LanSceneStateUpdate]:
    """从 ``gateway_post.prop`` 或 ``device_post.prop`` 消息中提取场景状态变更。

    协议规范：属性同步消息可包含 scenes 数组，每个场景有 id 和 state。
    """
    if message.get("method") not in _PROP_METHODS:
        return []
    scenes = message.get("scenes")
    if not isinstance(scenes, list):
        return []
    updates: list[LanSceneStateUpdate] = []
    for scene in scenes:
        if not isinstance(scene, Mapping):
            continue
        scene_id = to_int(scene.get("id"))
        params = scene.get("params")
        state = params.get("state") if isinstance(params, Mapping) else None
        if scene_id is not None and isinstance(state, str):
            name = scene.get("n") or scene.get("name")
            updates.append(
                LanSceneStateUpdate(
                    scene_id=scene_id,
                    name=str(name).strip() if name not in (None, "") else None,
                    state=state,
                )
            )
    return updates


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
    "LanSceneStateUpdate",
    "LanTopologyUpdate",
    "YeelightLanPropertyUpdate",
    "lan_event_payloads",
    "lan_property_updates",
    "lan_scene_updates",
    "lan_topology_update",
]
