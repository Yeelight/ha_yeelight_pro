"""Yeelight Pro 门锁投影模块.

将设备运行时数据投影为 Home Assistant 门锁实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..utils import to_bool, to_category, matches_category
from .device import flatten_instance_state, project_payload_device_info

LOCK_CATEGORY_TOKENS = ("lock", "door lock", "smart lock", "门锁", "智能锁")
LOCK_STATE_KEYS = ("lock", "locked", "lck")


@dataclass(slots=True)
class HALockProjection:
    """设备运行时数据投影后的 Home Assistant 门锁视图。"""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    is_locked: bool
    control_key: str
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_lock(device_payload: Mapping[str, Any], *, domain: str) -> HALockProjection | None:
    """将协调器设备载荷投影为 Home Assistant 门锁视图。"""
    instance = _load_instance(device_payload)
    component = _select_lock_component(instance)
    params = _runtime_state(device_payload, instance, component)
    if not _looks_like_lock(device_payload, params):
        return None

    control_key = _control_key(params)
    device_id = str(device_payload.get("device_id", "unknown"))
    available = to_bool(device_payload.get("online"), default=False)
    if instance is not None:
        available = bool(instance.online)
    if instance is not None and component is not None:
        available = bool(instance.online and component.available)

    return HALockProjection(
        component_id="lock",
        unique_id=f"{domain}_{device_id}_lock",
        name=None,
        available=available,
        is_locked=to_bool(params.get(control_key), default=False),
        control_key=control_key,
        device_info=project_payload_device_info(device_payload, instance),
        icon="mdi:lock",
    )


def _looks_like_lock(device_payload: Mapping[str, Any], params: Mapping[str, Any]) -> bool:
    """判断设备载荷是否属于门锁类型。"""
    if device_payload.get("type") == "lock":
        return True
    category = to_category(device_payload.get("category", ""))
    if category and matches_category(category, LOCK_CATEGORY_TOKENS):
        return True
    return any(key in params for key in LOCK_STATE_KEYS)


def _control_key(params: Mapping[str, Any]) -> str:
    """从运行时参数中选择门锁状态键。"""
    for key in LOCK_STATE_KEYS:
        if key in params:
            return key
    return "lock"


def _load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从载荷中加载设备实例模型。"""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """从载荷中提取运行时参数。"""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _select_lock_component(
    instance: HADeviceInstanceModel | None,
) -> ComponentInstanceModel | None:
    """从设备实例中选择门锁组件。"""
    if instance is None:
        return None

    for component in instance.components:
        category = to_category(component.category)
        if category and matches_category(category, LOCK_CATEGORY_TOKENS):
            return component
        if any(key in component.state for key in LOCK_STATE_KEYS):
            return component
    return None


def _runtime_state(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    component: ComponentInstanceModel | None,
) -> dict[str, Any]:
    """合并运行时状态：组件状态优先，回退到实例展平状态和载荷参数。"""
    if component is not None:
        merged = _params(device_payload)
        merged.update(component.state)
        return merged

    state = flatten_instance_state(instance)
    if state:
        return state
    return _params(device_payload)
