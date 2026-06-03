"""将协调器运行时数据投影为 Home Assistant switch 视图.

迁移自 lucore_gateway/projector/switch.py，
使用 yeelight_pro.utils 提供的通用工具函数。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..utils import to_bool, to_int, to_str, to_category, matches_category
from .device import project_device_info

RAW_SWITCH_KEY_RE = re.compile(r"^(?P<index>\d+)-(?P<prop>p|sp)$")
COMPONENT_INDEX_RE = re.compile(r"_(?P<index>\d+)$")
DIRECT_SWITCH_PROPS = ("p", "sp")
SWITCH_TOKENS = ("switch", "relay", "outlet")
LIGHT_TOKENS = ("light", "lamp")
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
)


@dataclass(slots=True)
class HASwitchProjection:
    """投影后的 Home Assistant switch 视图."""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    is_on: bool
    control_key: str
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_switches(
    device_payload: Mapping[str, Any], *, domain: str
) -> list[HASwitchProjection]:
    """将协调器 payload 投影为一个或多个 Home Assistant switch 实体.

    优先基于实例模型投影，若无匹配则回退到原始参数投影。
    """
    instance = _load_instance(device_payload)
    projections = _project_instance_switches(device_payload, instance, domain=domain)
    if projections:
        return projections
    return _project_raw_switches(device_payload, instance, domain=domain)


# ---------------------------------------------------------------------------
# 实例模型投影
# ---------------------------------------------------------------------------


def _project_instance_switches(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    *,
    domain: str,
) -> list[HASwitchProjection]:
    """基于 HADeviceInstanceModel 投影 switch 组件."""
    if instance is None:
        return []

    base_name = instance.name or to_str(device_payload.get("name"))
    device_info = project_device_info(instance)
    params = _params(device_payload)
    key_map = _component_state_key_map(instance)
    projections: list[HASwitchProjection] = []

    for component in instance.components:
        if not _looks_like_switch_component(component):
            continue
        if _extract_indexed_switch_keys(component.state):
            continue

        prop = _direct_switch_prop(component.state)
        if prop is None:
            continue

        control_key = _resolve_component_control_key(
            component.component_id,
            prop,
            params=params,
            key_map=key_map,
        )
        projections.append(
            HASwitchProjection(
                component_id=component.component_id,
                unique_id=f"{domain}_{instance.device_id}_{component.component_id}",
                name=_build_switch_name(base_name, component.component_id, control_key),
                available=bool(instance.online and component.available),
                is_on=bool(component.state.get(prop)),
                control_key=control_key,
                device_info=device_info,
                icon="mdi:light-switch",
            )
        )

    return projections


# ---------------------------------------------------------------------------
# 原始参数投影（回退路径）
# ---------------------------------------------------------------------------


def _project_raw_switches(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    *,
    domain: str,
) -> list[HASwitchProjection]:
    """基于原始 params 投影 switch（无实例模型时的回退路径）."""
    params = _params(device_payload)
    device_id = str(device_payload.get("device_id", "unknown"))
    base_name = to_str(device_payload.get("name")) or device_id
    device_info = project_device_info(instance) if instance is not None else None
    available = to_bool(device_payload.get("online"), default=False)

    raw_keys = _extract_indexed_switch_keys(params)
    if raw_keys:
        projections: list[HASwitchProjection] = []
        for raw_key in raw_keys:
            component_id = _component_id_from_raw_key(raw_key)
            projections.append(
                HASwitchProjection(
                    component_id=component_id,
                    unique_id=f"{domain}_{device_id}_{component_id}",
                    name=_build_switch_name(base_name, component_id, raw_key),
                    available=available,
                    is_on=bool(params.get(raw_key)),
                    control_key=raw_key,
                    device_info=device_info,
                    icon="mdi:light-switch",
                )
            )
        return projections

    if device_payload.get("type") not in {"switch", "outlet"}:
        return []

    direct_prop = _direct_switch_prop(params) or "p"
    component_id = "switch"
    return [
        HASwitchProjection(
            component_id=component_id,
            unique_id=f"{domain}_{device_id}_{component_id}",
            name=base_name,
            available=available,
            is_on=bool(params.get(direct_prop, params.get("on", False))),
            control_key=direct_prop,
            device_info=device_info,
            icon="mdi:light-switch",
        )
    ]


# ---------------------------------------------------------------------------
# 辅助：实例加载与组件判断
# ---------------------------------------------------------------------------


def _load_instance(
    device_payload: Mapping[str, Any],
) -> HADeviceInstanceModel | None:
    """从 payload 中加载 HADeviceInstanceModel."""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


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
    """判断组件是否表现为 switch 类型.

    依次通过 category、component_id、features 排除/确认。
    """
    lowered = component.component_id.lower()
    category = to_category(component.category)

    if matches_category(category, LIGHT_TOKENS + ("灯", "灯带", "彩光", "色温")):
        return False
    if matches_category(category, NON_SWITCH_TOKENS):
        return False
    if matches_category(category, SWITCH_TOKENS + ("开关", "面板")):
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
    if {"brightness", "color_temp", "rgb", "speed", "direction", "mode", "position", "lock"} & features:
        return False

    if any(token in lowered for token in SWITCH_TOKENS):
        return True
    return _direct_switch_prop(component.state) is not None


# ---------------------------------------------------------------------------
# 辅助：控制键解析
# ---------------------------------------------------------------------------


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
    """解析组件的实际控制键.

    优先使用 key_map 映射，其次根据组件索引推导。
    """
    mapped = key_map.get(component_id, {}).get(prop)
    if mapped:
        return mapped

    index = _component_index(component_id)
    if index is not None:
        candidate = f"{index}-{prop}"
        if candidate in params or not params:
            return candidate
    return prop


def _component_index(component_id: str) -> int | None:
    """从 component_id 中提取数字索引."""
    match = COMPONENT_INDEX_RE.search(component_id)
    if not match:
        return None
    return to_int(match.group("index"))


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
    index = _component_index(component_id)
    if index is None:
        match = RAW_SWITCH_KEY_RE.match(control_key)
        if match:
            index = to_int(match.group("index"))
    if index is None:
        return None
    return str(index)


# ---------------------------------------------------------------------------
# 辅助：数据提取
# ---------------------------------------------------------------------------


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
