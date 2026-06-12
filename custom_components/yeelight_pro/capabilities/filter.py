"""Yeelight IoT 能力过滤规则.

这里集中处理“上游物模型未知能力是否可见”的本地策略，避免各平台各自
放宽实体生成边界。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Any

from ..utils import matches_category, to_category, to_str
from .registry import (
    iot_registry,
    normalize_alias_key,
    parse_component_property_key,
    platform_for_category,
    property_spec,
)

UNKNOWN_CAPABILITY_REASON = "unknown_capability"
FALLBACK_SENSOR_REASON = "fallback_sensor"
UNSUPPORTED_PLATFORM_REASON = "unsupported_platform"
UNSUPPORTED_VALUE_REASON = "unsupported_value"

_EVENT_INPUT_CATEGORIES = frozenset({"scene_panel", "knob_switch"})
_LOW_CONFIDENCE_COMPONENT_TOKENS = (
    "audio",
    "wifi_screen",
    "wifi screen",
    "mesh_screen",
    "mesh screen",
    "knob_screen",
    "knob screen",
    "panorama_screen",
    "panorama screen",
    "knx",
    "matter",
    "thread",
    "vendor_bridge",
    "vendor bridge",
    "声音",
    "wifi屏",
    "mesh屏",
    "旋钮屏",
    "全景屏",
)
_BRIDGE_PROTOCOL_TOKENS = ("matter", "thread", "dali")
_UNKNOWN_ID_RE = re.compile(r"[^a-z0-9_]+")


@dataclass(frozen=True, slots=True)
class CapabilityFilterDecision:
    """单个能力是否允许投影的判定结果."""

    allowed: bool
    reason: str | None = None


def is_known_property_key(value: Any) -> bool:
    """判断原始状态 key 是否能解析为已登记 Yeelight IoT 属性."""
    try:
        prop_name = parse_component_property_key(value).prop_name
    except ValueError:
        return False
    return property_spec(prop_name) is not None


def should_project_unknown_property(
    prop_key: Any,
    value: Any,
    device_payload: Mapping[str, Any],
    *,
    platform: str,
    hide_unknown_entities: bool,
) -> CapabilityFilterDecision:
    """判断未知属性是否可以作为受控 fallback 实体投影."""
    if is_known_property_key(prop_key):
        return CapabilityFilterDecision(False, None)
    if hide_unknown_entities:
        return CapabilityFilterDecision(False, UNKNOWN_CAPABILITY_REASON)
    if is_low_confidence_component_payload(device_payload):
        return CapabilityFilterDecision(False, UNSUPPORTED_PLATFORM_REASON)
    if platform != "sensor" or not _supports_unknown_sensor_fallback(device_payload):
        return CapabilityFilterDecision(False, UNSUPPORTED_PLATFORM_REASON)
    if not _is_fallback_sensor_value(value):
        return CapabilityFilterDecision(False, UNSUPPORTED_VALUE_REASON)
    return CapabilityFilterDecision(True, FALLBACK_SENSOR_REASON)


def unknown_sensor_component_id(prop_key: Any) -> str:
    """返回未知 sensor fallback 的稳定 component_id."""
    normalized = normalize_alias_key(prop_key)
    normalized = _UNKNOWN_ID_RE.sub("_", normalized).strip("_")
    return f"unknown_{normalized or 'property'}"


def unknown_sensor_name(prop_key: Any) -> str:
    """返回未知 sensor fallback 的实体名称."""
    try:
        prop_name = parse_component_property_key(prop_key).prop_name
    except ValueError:
        prop_name = str(prop_key)
    return f"未知 {prop_name}"


def summarize_unknown_capabilities(
    devices: list[Mapping[str, Any]],
    *,
    hide_unknown_entities: bool,
) -> dict[str, Any]:
    """返回未知能力过滤的脱敏聚合摘要."""
    hidden = 0
    fallback = 0
    unsupported = 0
    for device_payload in devices:
        for prop_key, value in _runtime_state(device_payload).items():
            decision = should_project_unknown_property(
                prop_key,
                value,
                device_payload,
                platform="sensor",
                hide_unknown_entities=hide_unknown_entities,
            )
            if decision.allowed:
                fallback += 1
            elif decision.reason == UNKNOWN_CAPABILITY_REASON:
                hidden += 1
            elif decision.reason in {UNSUPPORTED_PLATFORM_REASON, UNSUPPORTED_VALUE_REASON}:
                unsupported += 1
    return {
        "hidden_unknown_properties": hidden,
        "fallback_sensor_properties": fallback,
        "unsupported_unknown_properties": unsupported,
    }


def is_low_confidence_component_payload(device_payload: Mapping[str, Any]) -> bool:
    """Return whether fallback projection needs samples before exposure."""
    return bool(
        _payload_has_token(device_payload, _LOW_CONFIDENCE_COMPONENT_TOKENS)
        or _payload_has_bridge_protocol(device_payload)
    )


def _supports_unknown_sensor_fallback(device_payload: Mapping[str, Any]) -> bool:
    """仅 sensor 类来源允许未知只读 fallback，事件/控制类不放宽."""
    category = to_category(
        device_payload.get("effective_category")
        or device_payload.get("iot_category")
        or device_payload.get("category")
    )
    source_type = to_category(device_payload.get("type"))
    if _is_event_input_identity(category) or _is_event_input_identity(source_type):
        return False
    return source_type == "sensor" or platform_for_category(category) == "sensor"


def _payload_has_token(
    device_payload: Mapping[str, Any],
    tokens: tuple[str, ...],
) -> bool:
    """Check device, component, and product categories for conservative tokens."""
    values = [
        device_payload.get("category"),
        device_payload.get("type"),
        device_payload.get("component_id"),
    ]
    instance = device_payload.get("ha_device_instance")
    if isinstance(instance, Mapping):
        values.extend(_component_values(instance.get("components")))
    product_model = device_payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        product = product_model.get("product")
        if isinstance(product, Mapping):
            values.extend((product.get("category"), product.get("model")))
        values.extend(_component_values(product_model.get("components")))
    return any(matches_category(to_category(value), tokens) for value in values)


def _is_event_input_identity(value: Any) -> bool:
    """Return true for documented event-input categories or components."""
    category = to_category(value)
    if category in _EVENT_INPUT_CATEGORIES:
        return True
    spec = iot_registry().component_map.get(_component_key(value))
    return spec is not None and spec.category in _EVENT_INPUT_CATEGORIES


def _component_key(value: Any) -> str:
    text = to_str(value)
    if not text:
        return ""
    return " ".join(text.lower().replace("_", " ").replace("-", " ").split())


def _payload_has_bridge_protocol(device_payload: Mapping[str, Any]) -> bool:
    """Treat bridge-only protocols as metadata, not fallback entity confidence."""
    product_model = device_payload.get("ha_product_model")
    if not isinstance(product_model, Mapping):
        return False
    product = product_model.get("product")
    if not isinstance(product, Mapping):
        return False
    bridge = product.get("bridge")
    if not isinstance(bridge, Mapping):
        return False
    protocols = bridge.get("protocols")
    if not isinstance(protocols, list):
        return False
    return any(
        matches_category(to_category(item), _BRIDGE_PROTOCOL_TOKENS)
        for item in protocols
    )


def _component_values(value: Any) -> list[Any]:
    """Return category-like values from component payloads."""
    if not isinstance(value, list):
        return []
    values: list[Any] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        values.extend(
            (
                item.get("category"),
                item.get("component_id"),
                item.get("name"),
                item.get("desc"),
            )
        )
    return values


def _is_fallback_sensor_value(value: Any) -> bool:
    """未知 fallback sensor 只接受简单只读标量，避免暴露控制语义."""
    return value is not None and not isinstance(
        value,
        (bool, Mapping, list, tuple, set),
    )


def _runtime_state(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """提取 params 与 canonical component state 的简化状态视图."""
    merged: dict[str, Any] = {}
    params = device_payload.get("params")
    if isinstance(params, Mapping):
        merged.update(params)

    instance = device_payload.get("ha_device_instance")
    if not isinstance(instance, Mapping):
        return merged

    components = instance.get("components")
    if not isinstance(components, list):
        return merged

    for component in components:
        if not isinstance(component, Mapping):
            continue
        state = component.get("state")
        if isinstance(state, Mapping):
            merged.update(state)
    return merged
