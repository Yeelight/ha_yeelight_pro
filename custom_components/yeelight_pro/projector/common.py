"""Shared helpers for Yeelight Pro projector modules."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any, Mapping

from ..canonical.models import (
    ComponentInstanceModel,
    ComponentModel,
    HADeviceInstanceModel,
    HAProductModel,
)
from ..capabilities.registry import format_component_property_key
from ..core.device_structural_models import structural_component_label
from ..utils import to_bool, to_int

COMPONENT_INDEX_RE = re.compile(r"_(?P<index>\d+)$")
_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class NumericRange:
    """归一化的数值范围元数据。"""

    min: int | None = None
    max: int | None = None
    step: int | None = None


def load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从载荷中加载设备实例模型。"""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def load_product_model(device_payload: Mapping[str, Any]) -> HAProductModel | None:
    """从载荷中加载产品模型。"""
    payload = device_payload.get("ha_product_model")
    if not isinstance(payload, Mapping):
        return None
    return HAProductModel.from_dict(payload)


def product_component(
    product_model: HAProductModel | None,
    component_id: str,
) -> ComponentModel | None:
    """从产品模型中查找匹配的组件定义。"""
    if product_model is None:
        return None
    return next(
        (item for item in product_model.components if item.component_id == component_id),
        None,
    )


def component_index(component_id: str) -> int | None:
    """从组件 ID 中提取数字索引。"""
    if component_id.isdigit():
        return to_int(component_id)
    match = COMPONENT_INDEX_RE.search(component_id)
    if not match:
        return None
    return to_int(match.group("index"))


def component_state_key_map(
    instance: HADeviceInstanceModel,
) -> dict[str, dict[str, str]]:
    """构建 component_id -> {prop_id: raw_key} 的运行时状态键映射."""
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


def component_state_key(
    instance: HADeviceInstanceModel,
    component_id: str,
    prop_id: str,
) -> str:
    """返回组件属性在 params/state 中对应的真实 key."""
    mapped = component_state_key_map(instance).get(component_id, {}).get(prop_id)
    if mapped:
        return mapped
    return format_component_property_key(component_index(component_id), prop_id)


def state_value(state: Mapping[str, Any], control_or_state_key: str | None) -> Any:
    """按组件 scoped key 或普通属性 key 读取状态值."""
    if control_or_state_key is None:
        return None
    if control_or_state_key in state:
        return state.get(control_or_state_key)
    if "-" in control_or_state_key:
        return state.get(control_or_state_key.split("-", 1)[1])
    return state.get(control_or_state_key)


def component_property_value(
    state: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    prop_id: str,
) -> Any:
    """读取组件属性值，优先使用 canonical component.state."""
    if prop_id in component.state:
        return component.state.get(prop_id)
    control_key = component_state_key(instance, component.component_id, prop_id)
    if control_key in state and control_key != prop_id:
        _LOGGER.debug(
            "Projecting component-scoped state value: device_id=%s component_id=%s "
            "category=%s prop_id=%s control_key=%s action=component_scoped_state_read",
            instance.device_id,
            component.component_id,
            component.category,
            prop_id,
            control_key,
        )
    return component_scoped_state_value(state, control_key, instance, component, prop_id)


def component_scoped_state_value(
    state: Mapping[str, Any],
    control_key: str | None,
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    prop_id: str,
) -> Any:
    """按组件 scoped key 读值，避免多组件设备回退到裸属性造成串路."""
    if control_key is None:
        return None
    if control_key in state:
        return state.get(control_key)
    if control_key == prop_id:
        return state.get(prop_id)
    if "-" not in control_key:
        return state.get(control_key)
    if _can_fallback_to_plain_component_key(instance, component):
        return state.get(prop_id)
    return None


def _can_fallback_to_plain_component_key(
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
) -> bool:
    """Return true when plain-key fallback cannot collide with another component."""
    if component.index is not None:
        return False
    if component_index(component.component_id) is not None:
        return False
    return len(instance.components) == 1


def component_state_view(
    state: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    prop_ids: tuple[str, ...],
) -> dict[str, Any]:
    """返回带短属性别名的组件状态视图，保留原始 scoped key."""
    merged = dict(state)
    merged.update(component.state)
    for prop_id in prop_ids:
        control_key = component_state_key(instance, component.component_id, prop_id)
        if prop_id in component.state or prop_id in state or control_key in state:
            merged[prop_id] = component_property_value(state, instance, component, prop_id)
    return merged


def humanize_component_id(component_id: str) -> str | None:
    """将组件 ID 转换为人类可读名称。"""
    text = component_id.replace("_", " ").strip()
    return text or None


def component_display_label(component: ComponentInstanceModel) -> str | None:
    """Return a user-facing label for a component without leaking raw aliases."""
    structural = structural_component_label(_component_label_payload(component))
    if structural is not None:
        return structural
    for value in (component.name, component.desc):
        if text := _display_text(value):
            return text
    return humanize_component_id(component.component_id)


def _component_label_payload(component: ComponentInstanceModel) -> dict[str, Any]:
    return {
        "component_id": component.component_id,
        "name": component.name,
        "desc": component.desc,
        "category": component.category,
    }


def _display_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def schema_backed_component_available(
    device_online: bool | None,
    component: ComponentInstanceModel | None,
    *,
    schema_component: ComponentModel | None = None,
) -> bool:
    """计算组件实体可用性，避免 schema 有定义但读值暂缺时显示不可用."""
    if not to_bool(device_online, default=True):
        return False
    if component is None or component.available:
        return True
    return schema_component is not None and not component.state


def payload_available(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None = None,
) -> bool:
    """Return device availability, treating missing Open API online as available."""
    if instance is not None:
        return to_bool(instance.online, default=True)
    return to_bool(device_payload.get("online"), default=True)
