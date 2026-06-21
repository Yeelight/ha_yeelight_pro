"""Helper functions for Yeelight runtime device adapters."""

from __future__ import annotations

import re
from typing import Any, Mapping

from ..canonical.models import ValueRangeModel
from ..capabilities.registry import (
    component_platform_hint,
    is_projectable_global_component,
    platform_for_category,
    property_capability,
    property_spec,
)
from ..core.device_runtime_capabilities import normalize_iot_category
from ..utils import to_str

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
    "switch": {"p", "sp"},
    "binary_sensor": {"mv", "dc", "alm"},
    "sensor": {"t", "h", "luminance", "level"},
    "cover": {"cp", "tp"},
    "climate": {"acm", "actt", "acct", "acf", "aco"},
    "fresh_air": {"vmcp", "vmcf"},
    "temp_control": {"acp", "acm", "actt", "acct", "acf", "aco", "vmcp", "vmcf"},
}
INDEXED_RUNTIME_KEY_RE = re.compile(r"^\d+-(.+)$")
STATELESS_ACTUATOR_PLATFORMS = frozenset({"climate", "cover", "fan", "light", "switch"})
SENSOR_PLATFORMS = frozenset({"binary_sensor", "sensor"})
METADATA_GLOBAL_COMPONENTS = frozenset({"basic"})


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
    if bool(getattr(component, "events", None)):
        return True
    if to_str(getattr(component, "component_type", None)) == "global":
        if _component_identity(component) in METADATA_GLOBAL_COMPONENTS:
            return False
        return is_projectable_global_component(component) or has_writable_helper_property(
            component
        )
    if component_state:
        return True
    if _component_category(component) == "other":
        return has_writable_helper_property(component)
    if looks_like_sensor_component(component):
        return True
    return looks_like_stateless_actuator_component(component)


def should_expose_component_state(component: Any) -> bool:
    """判断组件是否应暴露运行时状态。"""
    component_type = to_str(getattr(component, "component_type", None))
    if component_type != "global":
        return True
    if _component_identity(component) in METADATA_GLOBAL_COMPONENTS:
        return False
    return is_projectable_global_component(component) or has_writable_helper_property(
        component
    )


def should_expose_runtime_property(component: Any, prop: Any) -> bool:
    """判断属性是否应暴露到运行时状态。"""
    if not should_expose_component_state(component):
        return False

    kind = to_str(getattr(prop, "kind", None))
    if kind in RUNTIME_EXCLUDED_KINDS:
        return False

    component_type = to_str(getattr(component, "component_type", None))
    if component_type == "global":
        return is_documented_global_runtime_property(prop)

    property_type = to_str(getattr(prop, "property_type", None))
    if kind == "config" or property_type == "config":
        return is_documented_runtime_config_property(prop)
    return property_type not in RUNTIME_EXCLUDED_PROPERTY_TYPES


def is_documented_global_runtime_property(prop: Any) -> bool:
    """全局组件只暴露官方诊断能力，配置/密钥不进入运行时状态。"""
    spec = property_spec(getattr(prop, "prop_id", None))
    if spec is None or not spec.readable or spec.category == "config":
        return False
    return property_capability(spec.prop) is not None


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
    """根据 registry/category 判断是否为无状态执行器。"""
    return _component_platform(component) in STATELESS_ACTUATOR_PLATFORMS


def looks_like_sensor_component(component: Any) -> bool:
    """根据易来品类或传感属性判断是否为只读传感组件。"""
    if _component_platform(component) in SENSOR_PLATFORMS:
        return True
    return any(
        to_str(getattr(prop, "prop_id", None)) in SENSOR_PROPERTY_KEYS
        for prop in getattr(component, "properties", []) or []
    )


def has_writable_helper_property(component: Any) -> bool:
    """Return true when docs/iot proves this empty component has helper controls."""
    return any(
        _is_writable_helper_property(prop)
        for prop in getattr(component, "properties", []) or []
    )


def _component_platform(component: Any) -> str | None:
    """返回 registry 支撑的 HA 平台，不读取用户可见名称。"""
    for value in (
        getattr(component, "component_id", None),
        getattr(component, "category", None),
        getattr(component, "cid", None),
    ):
        platform = component_platform_hint(value)
        if platform:
            return platform
        category = normalize_iot_category(value)
        if category == "other":
            continue
        if category:
            platform = platform_for_category(category)
            if platform:
                return platform
    return None


def _is_writable_helper_property(prop: Any) -> bool:
    prop_id = to_str(getattr(prop, "prop_id", None))
    if not prop_id:
        return False
    spec = property_spec(prop_id)
    if spec is None or not spec.writable:
        return False
    if to_str(getattr(prop, "format", None)) in {"jsonObj", "jsonArray"}:
        return False
    if not _property_access_allows_write(getattr(prop, "access", None)):
        return False
    return bool(
        _has_value_range(prop)
        or getattr(prop, "value_list", None)
        or (to_str(getattr(prop, "format", None)) or "").lower() in {"bool", "boolean"}
        or spec.data_type.lower() in {"bool", "boolean"}
    )


def _property_access_allows_write(value: Any) -> bool:
    text = (to_str(value) or "").lower()
    return "write" in text or "写" in text or text in {"rw", "read_write"}


def _has_value_range(prop: Any) -> bool:
    value_range = getattr(prop, "value_range", None)
    if value_range is None:
        return False
    if isinstance(value_range, ValueRangeModel):
        return any(
            value is not None
            for value in (value_range.min, value_range.max, value_range.step)
        )
    return bool(value_range)


def _component_category(component: Any) -> str | None:
    for value in (
        getattr(component, "component_id", None),
        getattr(component, "category", None),
        getattr(component, "cid", None),
    ):
        category = normalize_iot_category(value)
        if category:
            return category
    return None


def _has_safe_global_props(component: Any) -> bool:
    """Only keep documented global components that can project HA entities."""
    return any(
        to_str(getattr(prop, "prop_id", None)) in SENSOR_PROPERTY_KEYS
        or property_capability(getattr(prop, "prop_id", None)) is not None
        for prop in getattr(component, "properties", []) or []
    )


def _component_identity(component: Any) -> str:
    """Return the registry identity for global component boundary checks."""
    for value in (
        getattr(component, "component_id", None),
        getattr(component, "alias", None),
        getattr(component, "name", None),
    ):
        text = to_str(value)
        if text:
            return " ".join(
                text.strip().lower().replace("_", " ").replace("-", " ").split()
            )
    return ""


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
