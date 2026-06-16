"""Pure adapters for Yeelight Pro push payloads."""

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
from .event_support import safe_runtime_event_params
from .push_contract import PUSH_DATA_TYPE_EVENT, PUSH_DATA_TYPE_PROP
from .utils import to_int

PUSH_TYPE_EVENT = PUSH_DATA_TYPE_EVENT
PUSH_TYPE_PROP = PUSH_DATA_TYPE_PROP


@dataclass(frozen=True, slots=True)
class YeelightPushPropertyUpdate:
    """Normalized property update from a Yeelight push payload."""

    node_id: int
    node_type: int | None
    params: dict[str, Any]


def push_property_updates(payload: Mapping[str, Any]) -> list[YeelightPushPropertyUpdate]:
    """Normalize a Yeelight WebSocket ``prop`` payload into state updates."""
    payload = _data_payload(payload)
    if payload.get("type") != PUSH_TYPE_PROP:
        return []
    updates: list[YeelightPushPropertyUpdate] = []
    for node in _iter_nodes(payload):
        node_id = _node_id(node)
        params = _node_params(node)
        if node_id is None or not isinstance(params, Mapping):
            continue
        updates.append(
            YeelightPushPropertyUpdate(
                node_id=node_id,
                node_type=to_int(node.get("nt")),
                params=dict(params),
            )
        )
    return updates


def push_event_payloads(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize Yeelight WebSocket ``event`` payload nodes for runtime dispatch."""
    payload = _data_payload(payload)
    if payload.get("type") != PUSH_TYPE_EVENT:
        return []
    events: list[dict[str, Any]] = []
    message_meta = _message_meta(payload)
    for node in _iter_nodes(payload):
        node_id = _node_id(node)
        event_id = node.get("event")
        if node_id is None or event_id in (None, ""):
            continue
        attributes = dict(message_meta)
        node_type = to_int(node.get("nt"))
        if node_type is not None:
            attributes["node_type"] = node_type
        _add_safe_params(attributes, node, "params")
        attributes["raw_event"] = event_id
        events.append(
            {
                ATTR_SOURCE_DEVICE_ID: str(node_id),
                ATTR_COMPONENT_ID: _component_id(node),
                ATTR_EVENT_TYPE: event_id,
                ATTR_EVENT_ATTRIBUTES: attributes,
            }
        )
    return events


def _iter_nodes(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Yield mapping nodes from a push payload."""
    nodes = payload.get("nodes")
    if nodes is None and _looks_like_single_node(payload):
        nodes = [payload]
    if not isinstance(nodes, list):
        raise HomeAssistantError("Invalid Yeelight Pro push payload nodes")
    if not all(isinstance(node, Mapping) for node in nodes):
        raise HomeAssistantError("Invalid Yeelight Pro push payload node")
    return list(nodes)


def _data_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the WebSocket data object when transports wrap the documented frame."""
    data = payload.get("data")
    return data if isinstance(data, Mapping) else payload


def _looks_like_single_node(payload: Mapping[str, Any]) -> bool:
    """Return true for a documented data frame collapsed into one node object."""
    return payload.get("type") in {PUSH_TYPE_PROP, PUSH_TYPE_EVENT} and any(
        key in payload for key in ("id", "nodeId", "resId", "deviceId")
    )


def _node_id(node: Mapping[str, Any]) -> int | None:
    """Return node id from documented and Open API read/control aliases."""
    for key in ("id", "nodeId", "node_id", "resId", "res_id", "deviceId", "device_id"):
        node_id = to_int(node.get(key))
        if node_id is not None:
            return node_id
    return None


def _node_params(node: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return property params from documented and read-property result shapes."""
    params = node.get("params")
    if isinstance(params, Mapping):
        param_values = dict(params)
        if "o" not in param_values and "o" in node:
            param_values["o"] = node.get("o")
        return param_values
    properties = node.get("properties") or node.get("props")
    if isinstance(properties, list):
        property_values = _params_from_properties(properties)
        if property_values is not None and "o" not in property_values and "o" in node:
            property_values["o"] = node.get("o")
        return property_values
    prop_id = node.get("propId") or node.get("propName")
    if prop_id not in (None, "") and "value" in node:
        return {str(prop_id): node.get("value")}
    return None


def _params_from_properties(properties: list[Any]) -> dict[str, Any] | None:
    """Convert property rows into Yeelight runtime params."""
    params: dict[str, Any] = {}
    for prop in properties:
        if not isinstance(prop, Mapping):
            return None
        prop_id = prop.get("propId") or prop.get("propName")
        if prop_id in (None, "") or "value" not in prop:
            continue
        params[str(prop_id)] = prop.get("value")
    return params


def _message_meta(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return safe push message metadata for event attributes."""
    meta: dict[str, Any] = {}
    msg_id = payload.get("msgId")
    timestamp = payload.get("timestamp")
    version = payload.get("version")
    if msg_id not in (None, ""):
        meta["message_id"] = str(msg_id)
    if timestamp is not None:
        meta["timestamp"] = timestamp
    if version not in (None, ""):
        meta["version"] = str(version)
    return meta


def _component_id(node: Mapping[str, Any]) -> str:
    """Return a stable component identifier for pushed node events."""
    component_id = node.get("componentId") or node.get("component_id")
    if component_id not in (None, ""):
        return str(component_id)
    node_type = to_int(node.get("nt"))
    if node_type is not None:
        return f"node_type_{node_type}"
    return "push_event"


def _add_safe_params(
    attributes: dict[str, Any],
    node: Mapping[str, Any],
    key: str,
) -> None:
    """复制推送事件参数前过滤敏感标识。"""
    params = node.get(key)
    if isinstance(params, Mapping) and params:
        safe_params = safe_runtime_event_params(params)
        if safe_params:
            attributes[key] = safe_params


__all__ = [
    "PUSH_TYPE_EVENT",
    "PUSH_TYPE_PROP",
    "YeelightPushPropertyUpdate",
    "push_event_payloads",
    "push_property_updates",
]
