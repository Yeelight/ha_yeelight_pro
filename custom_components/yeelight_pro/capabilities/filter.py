"""Yeelight IoT 能力过滤规则.

这里集中处理“上游物模型未知能力是否可见”的本地策略，避免各平台各自
放宽实体生成边界。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Any

from ..utils import matches_category, to_category
from .registry import (
    normalize_alias_key,
    parse_component_property_key,
    platform_for_category,
    property_spec,
)

UNKNOWN_CAPABILITY_REASON = "unknown_capability"
FALLBACK_SENSOR_REASON = "fallback_sensor"
UNSUPPORTED_PLATFORM_REASON = "unsupported_platform"
UNSUPPORTED_VALUE_REASON = "unsupported_value"

_EVENT_INPUT_TOKENS = (
    "scene_panel",
    "knob_switch",
    "button",
    "remote",
    "knob",
    "dial",
    "情景",
    "旋钮",
)
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


def _supports_unknown_sensor_fallback(device_payload: Mapping[str, Any]) -> bool:
    """仅 sensor 类来源允许未知只读 fallback，事件/控制类不放宽."""
    category = to_category(device_payload.get("category"))
    source_type = to_category(device_payload.get("type"))
    if matches_category(category, _EVENT_INPUT_TOKENS) or matches_category(
        source_type,
        _EVENT_INPUT_TOKENS,
    ):
        return False
    return source_type == "sensor" or platform_for_category(category) == "sensor"


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
