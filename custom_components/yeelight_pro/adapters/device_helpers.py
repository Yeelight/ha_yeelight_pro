"""Helper functions for Yeelight runtime device adapters."""

from __future__ import annotations

import re
from typing import Any, Mapping

from ..capabilities.registry import property_spec
from ..utils import to_str

RUNTIME_EXCLUDED_COMPONENT_TYPES = {"global"}
RUNTIME_EXCLUDED_KINDS = {"diagnostic", "info"}
RUNTIME_EXCLUDED_PROPERTY_TYPES = {"config"}
SENSOR_PROPERTY_KEYS = {
    "acct",
    "ae",
    "alm",
    "ap",
    "bl",
    "curp",
    "dc",
    "h",
    "iec",
    "level",
    "luminance",
    "mv",
    "rfhct",
    "t",
    "temp",
}
FALLBACK_RUNTIME_KEYS: dict[str, set[str]] = {
    "light": {"p", "sp", "l", "ct", "c", "m"},
    "fan": {"p", "lv", "dir", "m"},
    "switch": {"p", "sp", "on"},
    "outlet": {"p", "sp", "on"},
    "binary_sensor": {"mv", "dc", "alm"},
    "sensor": {"t", "h", "luminance", "level"},
    "cover": {"cp", "tp"},
    "climate": {"acm", "actt", "acct", "acf", "aco"},
}
INDEXED_RUNTIME_KEY_RE = re.compile(r"^\d+-(.+)$")
STATELESS_ACTUATOR_CATEGORY_TOKENS = (
    "light",
    "lamp",
    "灯",
    "灯带",
    "彩光",
    "色温",
    "switch",
    "relay",
    "outlet",
    "fan",
    "ceiling fan",
    "开关",
    "面板",
    "风扇",
    "吊扇",
    "cover",
    "curtain",
    "blind",
    "窗帘",
    "climate",
    "air",
    "heater",
    "bath",
    "空调",
    "浴霸",
)


def fallback_runtime_state(
    payload: Mapping[str, Any],
    params: Mapping[str, Any],
) -> dict[str, Any]:
    """无产品模型时提取允许暴露的运行时状态。"""
    source_type = to_str(payload.get("type"))
    allowed = FALLBACK_RUNTIME_KEYS.get(source_type or "", set())
    if not allowed:
        return {}

    state: dict[str, Any] = {}
    for raw_key, value in params.items():
        key = to_str(raw_key)
        if not key:
            continue
        if key in allowed or matches_indexed_runtime_key(key, allowed):
            state[key] = value
    return state


def matches_indexed_runtime_key(raw_key: str, allowed: set[str]) -> bool:
    """检查索引格式 key（如 '0-p'）是否匹配允许集合。"""
    matched = INDEXED_RUNTIME_KEY_RE.match(raw_key)
    if matched is None:
        return False
    return matched.group(1) in allowed


def should_include_runtime_component(
    component: Any,
    component_state: Mapping[str, Any],
) -> bool:
    """判断是否应暴露该运行时组件。"""
    if component_state:
        return True
    if bool(getattr(component, "events", None)):
        return True
    if looks_like_sensor_component(component):
        return True
    return looks_like_stateless_actuator_component(component)


def should_expose_component_state(component: Any) -> bool:
    """判断组件是否应暴露运行时状态。"""
    component_type = to_str(getattr(component, "component_type", None))
    return component_type not in RUNTIME_EXCLUDED_COMPONENT_TYPES


def should_expose_runtime_property(component: Any, prop: Any) -> bool:
    """判断属性是否应暴露到运行时状态。"""
    if not should_expose_component_state(component):
        return False

    kind = to_str(getattr(prop, "kind", None))
    if kind in RUNTIME_EXCLUDED_KINDS:
        return False

    property_type = to_str(getattr(prop, "property_type", None))
    if kind == "config" or property_type == "config":
        return is_documented_runtime_config_property(prop)
    return property_type not in RUNTIME_EXCLUDED_PROPERTY_TYPES


def is_documented_runtime_config_property(prop: Any) -> bool:
    """只保留 registry 证明可读的普通组件配置状态。"""
    spec = property_spec(getattr(prop, "prop_id", None))
    return bool(spec is not None and spec.readable)


def prefer_plain_match(
    candidates: list[str],
    component_by_id: Mapping[str, Any],
    raw_key: str,
) -> str | None:
    """多候选时优先匹配 global 组件的特定 key。"""
    global_candidates = [
        component_id
        for component_id in candidates
        if getattr(component_by_id.get(component_id), "component_type", None) == "global"
    ]
    if raw_key in {"fv", "name", "icon", "o"} and len(global_candidates) == 1:
        return global_candidates[0]
    return None


def looks_like_stateless_actuator_component(component: Any) -> bool:
    """根据类别或组件 ID 判断是否为无状态执行器。"""
    category = (to_str(getattr(component, "category", None)) or "").lower()
    component_id = (to_str(getattr(component, "component_id", None)) or "").lower()
    haystacks = (category, component_id)
    return any(
        token in haystack
        for haystack in haystacks
        for token in STATELESS_ACTUATOR_CATEGORY_TOKENS
    )


def looks_like_sensor_component(component: Any) -> bool:
    """Return true for known read-only sensor components even before first value."""
    category = (to_str(getattr(component, "category", None)) or "").lower()
    component_id = (to_str(getattr(component, "component_id", None)) or "").lower()
    haystacks = (category, component_id)
    if any(
        token in haystack
        for haystack in haystacks
        for token in ("sensor", "contact", "motion", "presence", "occupancy")
    ):
        return True
    return any(
        to_str(getattr(prop, "prop_id", None)) in SENSOR_PROPERTY_KEYS
        for prop in getattr(component, "properties", []) or []
    )


def normalize_pair_list(value: Any) -> list[list[str]]:
    """规范化二元组列表（如 identifiers、connections）。"""
    pairs: list[list[str]] = []
    for item in value or []:
        normalized = normalize_pair(item)
        if normalized:
            pairs.append(normalized)
    return pairs


def normalize_pair(value: Any) -> list[str] | None:
    """规范化单个二元组。"""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return [str(value[0]), str(value[1])]
    return None


def fallback_component_key(payload: Mapping[str, Any]) -> str:
    """无产品模型时的回退组件 key 提取。"""
    device_type = to_str(payload.get("type"))
    if device_type:
        return device_type
    return "main"
