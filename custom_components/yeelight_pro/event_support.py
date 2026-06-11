"""Shared helpers for Yeelight Pro event-style devices."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .capabilities.events import normalize_event_type
from .const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
)
from .event_identity import (
    SAFETY_EVENT_COMPONENT_ID,
    is_safety_event_device,
    is_safety_event_type,
)

SENSITIVE_RUNTIME_EVENT_PARAM_KEYS = frozenset(
    {"accesstoken", "deviceid", "did", "ip", "ipaddress", "mac", "macaddress", "token"}
)


@dataclass(slots=True)
class YeelightRuntimeEvent:
    """Normalized runtime event delivered inside the integration."""

    source_device_id: str
    component_id: str
    event_type: str
    event_attributes: dict[str, Any]


def normalize_runtime_event_payload(data: Mapping[str, Any]) -> YeelightRuntimeEvent:
    """Normalize an external or debug payload into the integration event shape."""
    event_type = normalize_event_type(data.get(ATTR_EVENT_TYPE))
    if event_type is None:
        raise HomeAssistantError("Invalid Yeelight Pro event type")

    source_device_id = data.get(ATTR_SOURCE_DEVICE_ID)
    component_id = data.get(ATTR_COMPONENT_ID)
    if source_device_id is None or str(source_device_id) == "":
        raise HomeAssistantError("Missing Yeelight Pro event source_device_id")
    if component_id is None or str(component_id) == "":
        raise HomeAssistantError("Missing Yeelight Pro event component_id")

    attributes = data.get(ATTR_EVENT_ATTRIBUTES)
    event_attributes = dict(attributes) if isinstance(attributes, Mapping) else {}
    return YeelightRuntimeEvent(
        source_device_id=str(source_device_id),
        component_id=str(component_id),
        event_type=event_type,
        event_attributes=event_attributes,
    )


def infer_event_component_id(
    payload: Mapping[str, Any],
    device_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """根据产品事件定义补全推送事件的 component_id.

    推送 payload 有时只携带节点类型和事件 ID。只有当前设备 schema 中
    存在唯一事件匹配时才替换 fallback component，避免误路由自动化。
    """
    result = dict(payload)
    component_id = str(result.get(ATTR_COMPONENT_ID, ""))
    if component_id and not _is_fallback_component_id(component_id):
        return result

    event_type = normalize_event_type(result.get(ATTR_EVENT_TYPE))
    if event_type is None or not isinstance(device_payload, Mapping):
        return result

    product_model = device_payload.get("ha_product_model")
    if not isinstance(product_model, Mapping):
        return result

    matches = {
        candidate
        for candidate in _matching_event_components(product_model, event_type)
    }
    if len(matches) == 1:
        result[ATTR_COMPONENT_ID] = next(iter(matches))
    elif is_safety_event_type(event_type) and is_safety_event_device(device_payload):
        result[ATTR_COMPONENT_ID] = SAFETY_EVENT_COMPONENT_ID
    return result


def runtime_event_to_bus_payload(event: YeelightRuntimeEvent) -> dict[str, Any]:
    """Convert a normalized runtime event into the HA bus payload."""
    return {
        ATTR_SOURCE_DEVICE_ID: event.source_device_id,
        ATTR_COMPONENT_ID: event.component_id,
        ATTR_EVENT_TYPE: event.event_type,
        ATTR_EVENT_ATTRIBUTES: dict(event.event_attributes),
    }


def safe_runtime_event_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """保留自动化事件参数，同时过滤凭据和设备标识。"""
    safe: dict[str, Any] = {}
    for key, value in params.items():
        key_text = str(key)
        normalized = "".join(char for char in key_text.casefold() if char.isalnum())
        if normalized in SENSITIVE_RUNTIME_EVENT_PARAM_KEYS:
            continue
        safe[key_text] = value
    return safe


def _is_fallback_component_id(component_id: str) -> bool:
    """判断 component_id 是否来自推送 adapter 的保守 fallback."""
    return component_id in {"lan_event", "push_event"} or component_id.startswith(
        "node_type_"
    )


def _matching_event_components(
    product_model: Mapping[str, Any],
    event_type: str,
) -> list[str]:
    """返回声明指定事件类型的 component_id 列表."""
    components = product_model.get("components")
    if not isinstance(components, list):
        return []

    matches: list[str] = []
    for component in components:
        if not isinstance(component, Mapping):
            continue
        component_id = str(
            component.get("component_id", component.get("componentId", ""))
        )
        if not component_id:
            continue
        if _component_declares_event(component, event_type):
            matches.append(component_id)
    return matches


def _component_declares_event(
    component: Mapping[str, Any],
    event_type: str,
) -> bool:
    """判断组件是否声明了指定的规范化事件类型."""
    events = component.get("events")
    if not isinstance(events, list):
        return False

    for event in events:
        if not isinstance(event, Mapping):
            continue
        normalized = (
            normalize_event_type(event.get("semantic"))
            or normalize_event_type(event.get("name"))
            or normalize_event_type(event.get("desc"))
        )
        if normalized is None:
            normalized = normalize_event_type(
                event.get("event_id", event.get("eventId"))
            )
        if normalized == event_type:
            return True
    return False


__all__ = [
    "YeelightRuntimeEvent",
    "SENSITIVE_RUNTIME_EVENT_PARAM_KEYS",
    "infer_event_component_id",
    "normalize_event_type",
    "normalize_runtime_event_payload",
    "runtime_event_to_bus_payload",
    "safe_runtime_event_params",
]
