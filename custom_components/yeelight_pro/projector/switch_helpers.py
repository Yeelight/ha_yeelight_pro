"""Switch-specific helper functions for Yeelight Pro projections."""

from __future__ import annotations

import re
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..capabilities.registry import (
    component_platform_hint,
    format_component_property_key,
    platform_for_category,
)
from ..device_display import channel_name_label, switch_channel_count_hint
from ..utils import to_category, to_int
from .common import component_index
from .event_input import is_event_input_category, is_event_input_component
from .platform_evidence import component_has_switch_evidence

RAW_SWITCH_KEY_RE = re.compile(r"^(?P<index>\d+)-(?P<prop>p|sp)$")
DIRECT_SWITCH_PROPS = ("p", "sp")
SWITCH_PARENT_CATEGORIES = {"relay_switch", "switch"}
NON_SWITCH_PARENT_CATEGORIES = {
    "binary_sensor",
    "climate",
    "contact_sensor",
    "cover",
    "curtain",
    "fan",
    "gateway",
    "human_sensor",
    "knob_switch",
    "light",
    "light_sensor",
    "scene_panel",
    "sensor",
    "temp_control",
}

def _allows_switch_projection(device_payload: Mapping[str, Any]) -> bool:
    """Return false when the parent device category owns another HA platform."""
    parent_category = to_category(
        device_payload.get("iot_category") or device_payload.get("category")
    )
    if parent_category in NON_SWITCH_PARENT_CATEGORIES:
        return False
    return True


def _allows_component_switch_projection(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
) -> bool:
    """Allow schema-backed switch components on mixed-category products."""
    if _allows_switch_projection(device_payload):
        return True
    return any(_looks_like_switch_component(component) for component in instance.components)


def _allows_raw_switch_fallback(device_payload: Mapping[str, Any]) -> bool:
    """Return true when legacy raw params belong to a known switch device."""
    if not _allows_switch_projection(device_payload):
        return False

    parent_category = to_category(
        device_payload.get("iot_category") or device_payload.get("category")
    )
    if parent_category in SWITCH_PARENT_CATEGORIES:
        return True

    if platform_for_category(parent_category) == "switch":
        return True

    component_hint_values = (
        device_payload.get("component_id"),
        device_payload.get("component"),
    )
    if any(component_platform_hint(value) == "switch" for value in component_hint_values):
        return True

    if parent_category:
        return False
    return device_payload.get("type") == "switch"


def _component_state_key_map(
    instance: HADeviceInstanceModel,
) -> dict[str, dict[str, str]]:
    """构建 component_id -> {prop_id: raw_key} 的映射表."""
    raw = instance.extensions.get("component_state_keys")
    if not isinstance(raw, Mapping):
        return {}

    mapping: dict[str, dict[str, str]] = {}
    for component_id, value in raw.items():
        if not isinstance(value, Mapping):
            continue
        mapping[str(component_id)] = {
            str(prop_id): str(raw_key)
            for prop_id, raw_key in value.items()
            if raw_key is not None
        }
    return mapping


def _looks_like_switch_component(component: ComponentInstanceModel) -> bool:
    """判断组件是否具备官方 relay switch 证据."""
    category = to_category(component.category)

    if is_event_input_category(category):
        return False
    if is_event_input_component(component.component_id):
        return False

    features = {
        str(item).strip().lower()
        for item in (
            component.instance_capabilities.features
            if component.instance_capabilities is not None
            else []
        )
        if str(item).strip()
    }
    non_switch_features = {
        "brightness",
        "color_temp",
        "rgb",
        "speed",
        "direction",
        "mode",
        "position",
    }
    if non_switch_features & features:
        return False

    if component_has_switch_evidence(component):
        return True
    return bool(
        category.replace("_", " ") == "switch control"
        and _direct_switch_prop(component.state)
        and component_index(component.component_id) is not None
    )


def _direct_switch_prop(state: Mapping[str, Any]) -> str | None:
    """返回 state 中的直接开关属性（p/sp），存在索引键时返回 None."""
    if _extract_indexed_switch_keys(state):
        return None
    for prop in DIRECT_SWITCH_PROPS:
        if prop in state:
            return prop
    return None


def _extract_indexed_switch_keys(state: Mapping[str, Any]) -> list[str]:
    """提取并排序所有匹配 N-p/N-sp 模式的索引开关键."""
    keys = [str(key) for key in state.keys() if RAW_SWITCH_KEY_RE.match(str(key))]
    keys.sort(key=_raw_switch_sort_key)
    return keys


def _switch_channel_allowed(device_payload: Mapping[str, Any], index: int | None) -> bool:
    """Return false when product naming explicitly limits switch channel count."""
    if index is None:
        return True
    count = switch_channel_count_hint(device_payload)
    return count is None or index <= count


def _resolve_component_control_key(
    component_id: str,
    prop: str,
    *,
    params: Mapping[str, Any],
    key_map: Mapping[str, Mapping[str, str]],
) -> str:
    """解析组件的实际控制键，优先使用显式 key_map."""
    mapped = key_map.get(component_id, {}).get(prop)
    if mapped:
        return mapped

    index = component_index(component_id)
    if index is not None:
        candidate = format_component_property_key(index, prop)
        if candidate in params or not params:
            return candidate
    return prop


def _component_id_from_raw_key(raw_key: str) -> str:
    """将原始键（如 '1-p'）转换为 component_id（如 'switch_1'）."""
    match = RAW_SWITCH_KEY_RE.match(raw_key)
    if not match:
        return "switch"
    return f"switch_{match.group('index')}"


def _index_from_raw_key(raw_key: str) -> int | None:
    """Return indexed switch key index from N-p/N-sp control keys."""
    match = RAW_SWITCH_KEY_RE.match(raw_key)
    if match is None:
        return None
    return to_int(match.group("index"))


def _build_switch_name(
    base_name: str | None,
    component_id: str,
    control_key: str,
    component: ComponentInstanceModel | None = None,
    *,
    device_payload: Mapping[str, Any] | None = None,
) -> str | None:
    """构建 switch 显示名称，避免裸数字通道名."""
    index = component_index(component_id)
    if index is None:
        match = RAW_SWITCH_KEY_RE.match(control_key)
        if match:
            index = to_int(match.group("index"))
    return channel_name_label(
        index=index,
        component=component,
        device_payload=device_payload,
    )


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """从 payload 中提取 params 字典."""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _raw_switch_sort_key(raw_key: str) -> tuple[int, str]:
    """索引开关键的排序键：按数字索引升序."""
    match = RAW_SWITCH_KEY_RE.match(raw_key)
    if not match:
        return (9999, raw_key)
    return (to_int(match.group("index")) or 9999, raw_key)
