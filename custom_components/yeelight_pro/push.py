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
from .utils import to_int

PUSH_TYPE_EVENT = "event"
PUSH_TYPE_PROP = "prop"


@dataclass(frozen=True, slots=True)
class YeelightPushPropertyUpdate:
    """Normalized property update from a Yeelight push payload."""

    node_id: int
    node_type: int | None
    params: dict[str, Any]


def push_property_updates(payload: Mapping[str, Any]) -> list[YeelightPushPropertyUpdate]:
    """Normalize a Yeelight WebSocket ``prop`` payload into state updates."""
    if payload.get("type") != PUSH_TYPE_PROP:
        return []
    updates: list[YeelightPushPropertyUpdate] = []
    for node in _iter_nodes(payload):
        node_id = to_int(node.get("id"))
        params = node.get("params")
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
    if payload.get("type") != PUSH_TYPE_EVENT:
        return []
    events: list[dict[str, Any]] = []
    message_meta = _message_meta(payload)
    for node in _iter_nodes(payload):
        node_id = to_int(node.get("id"))
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
    if not isinstance(nodes, list):
        raise HomeAssistantError("Invalid Yeelight Pro push payload nodes")
    if not all(isinstance(node, Mapping) for node in nodes):
        raise HomeAssistantError("Invalid Yeelight Pro push payload node")
    return list(nodes)


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
