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
from ..utils import matches_category, to_category, to_int
from .common import component_index

RAW_SWITCH_KEY_RE = re.compile(r"^(?P<index>\d+)-(?P<prop>p|sp)$")
DIRECT_SWITCH_PROPS = ("p", "sp")
SWITCH_TOKENS = ("switch", "relay", "outlet")
LIGHT_TOKENS = ("light", "lamp")
EVENT_INPUT_TOKENS = ("scene_panel", "knob_switch", "button", "remote", "knob", "dial")
NON_SWITCH_TOKENS = (
    "fan",
    "ceiling fan",
    "cover",
    "curtain",
    "blind",
    "lock",
    "door lock",
    "climate",
    "heater",
    "风扇",
    "吊扇",
    "窗帘",
    "门锁",
    "空调",
    "浴霸",
    "情景",
    "旋钮",
)


def _allows_raw_switch_fallback(device_payload: Mapping[str, Any]) -> bool:
    """Return true when legacy raw params belong to a known switch device."""
    if device_payload.get("type") in {"switch", "outlet"}:
        return True

    category = to_category(device_payload.get("category"))
    if platform_for_category(category) == "switch":
        return True

    component_hint_values = (
        device_payload.get("component_id"),
        device_payload.get("component"),
        device_payload.get("component_name"),
    )
    return any(component_platform_hint(value) == "switch" for value in component_hint_values)


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
    """判断组件是否表现为 switch 类型."""
    lowered = component.component_id.lower()
    category = to_category(component.category)

    if matches_category(category, EVENT_INPUT_TOKENS):
        return False
    if any(token in lowered for token in EVENT_INPUT_TOKENS):
        return False
    if matches_category(category, LIGHT_TOKENS + ("灯", "灯带", "彩光", "色温")):
        return False
    if matches_category(category, NON_SWITCH_TOKENS):
        return False
    if matches_category(category, SWITCH_TOKENS + ("开关", "面板")):
        return True

    if component_platform_hint(category) == "switch":
        return True
    if component_platform_hint(component.component_id) == "switch":
        return True

    if any(token in lowered for token in LIGHT_TOKENS):
        return False
    if any(token in lowered for token in NON_SWITCH_TOKENS):
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
        "lock",
    }
    if non_switch_features & features:
        return False

    return any(token in lowered for token in SWITCH_TOKENS)


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


def _build_switch_name(
    base_name: str | None, component_id: str, control_key: str
) -> str | None:
    """构建 switch 显示名称，返回索引字符串或 None."""
    index = component_index(component_id)
    if index is None:
        match = RAW_SWITCH_KEY_RE.match(control_key)
        if match:
            index = to_int(match.group("index"))
    if index is None:
        return None
    return str(index)


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
