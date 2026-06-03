"""Yeelight Pro sensor 投影模块.

将协调器运行时数据投影为 Home Assistant sensor 实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from .device import flatten_instance_state, project_device_info

# 传感器规格：键为协调器参数中的属性名
SENSOR_SPECS: dict[str, dict[str, str | None]] = {
    "t": {
        "component_id": "temperature",
        "label": "温度",
        "device_class": "temperature",
        "unit": "°C",
        "icon": None,
    },
    "h": {
        "component_id": "humidity",
        "label": "湿度",
        "device_class": "humidity",
        "unit": "%",
        "icon": None,
    },
    "luminance": {
        "component_id": "illuminance",
        "label": "光照",
        "device_class": "illuminance",
        "unit": "lx",
        "icon": None,
    },
    "level": {
        "component_id": "light_level",
        "label": "光感等级",
        "device_class": None,
        "unit": None,
        "icon": "mdi:brightness-6",
    },
}


@dataclass(slots=True)
class HASensorProjection:
    """投影后的 Home Assistant sensor 实体视图。"""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    native_value: Any
    device_class: str | None
    native_unit_of_measurement: str | None
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_sensors(device_payload: Mapping[str, Any], *, domain: str) -> list[HASensorProjection]:
    """将协调器载荷投影为一组 sensor 视图。"""
    instance = _load_instance(device_payload)
    params = _runtime_state(device_payload, instance)
    device_info = project_device_info(instance) if instance is not None else None
    base_name = _device_name(device_payload, instance)
    device_id = str(device_payload.get("device_id", "unknown"))
    base_available = _bool(device_payload.get("online"), default=False)
    if instance is not None:
        base_available = bool(instance.online)

    projections: list[HASensorProjection] = []
    for key, spec in SENSOR_SPECS.items():
        if key not in params:
            continue
        component = _component_for_prop(instance, key)
        projections.append(
            HASensorProjection(
                component_id=str(spec["component_id"]),
                unique_id=f"{domain}_{device_id}_{spec['component_id']}",
                name=_projection_name(base_name, spec["label"]),
                available=_projection_available(base_available, component),
                native_value=params.get(key),
                device_class=_string(spec["device_class"]),
                native_unit_of_measurement=_string(spec["unit"]),
                device_info=device_info,
                icon=_string(spec["icon"]),
            )
        )

    return projections


# -- 辅助函数 ---------------------------------------------------------------


def _load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从载荷中解析 HADeviceInstanceModel 实例。"""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _device_name(
    device_payload: Mapping[str, Any], instance: HADeviceInstanceModel | None
) -> str | None:
    """获取设备名称，优先使用实例名称。"""
    if instance is not None and instance.name:
        return instance.name
    return _string(device_payload.get("name"))


def _projection_name(base_name: str | None, label: str | None) -> str | None:
    """返回投影实体名称（当前直接使用标签）。"""
    return label


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """从载荷中提取 params 字段。"""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _runtime_state(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
) -> dict[str, Any]:
    """合并载荷 params 与实例组件状态。"""
    merged = _params(device_payload)
    merged.update(flatten_instance_state(instance))
    return merged


def _component_for_prop(
    instance: HADeviceInstanceModel | None,
    prop_key: str,
) -> ComponentInstanceModel | None:
    """查找包含指定属性键的组件。"""
    if instance is None:
        return None
    for component in instance.components:
        if prop_key in component.state:
            return component
    return None


def _projection_available(
    base_available: bool,
    component: ComponentInstanceModel | None,
) -> bool:
    """计算投影实体的可用状态。"""
    if component is None:
        return base_available
    return bool(base_available and component.available)


def _bool(value: Any, default: bool = False) -> bool:
    """安全布尔值转换。"""
    if value is None:
        return default
    return bool(value)


def _string(value: Any) -> str | None:
    """安全字符串转换，空值返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
