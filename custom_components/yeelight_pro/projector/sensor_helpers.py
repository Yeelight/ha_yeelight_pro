"""Sensor-specific helper functions for Yeelight Pro projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..capabilities.registry import property_capability, property_spec
from ..utils import matches_category, to_category, to_int
from .device import flatten_instance_state

SENSOR_LABELS = {
    "t": ("temperature", "温度"),
    "h": ("humidity", "湿度"),
    "luminance": ("illuminance", "光照"),
    "curp": ("current_power", "当前功率"),
    "iec": ("energy_consumption", "阶段电量"),
    "ap": ("active_power", "有功功率"),
    "ae": ("active_energy", "总有功"),
}
REGISTRY_SENSOR_PROPS = frozenset(SENSOR_LABELS)
DALI_ENERGY_COMPONENT = "dali energy"
DALI_ENERGY_PROJECTED_PROPS = frozenset({"ap", "ae"})
LEGACY_SENSOR_SPECS: dict[str, dict[str, str | None]] = {
    "level": {
        "component_id": "light_level",
        "label": "光感等级",
        "device_class": None,
        "unit": None,
        "icon": "mdi:brightness-6",
    },
}

EVENT_STYLE_PRODUCT_TYPES = {128, 132}
EVENT_INPUT_TOKENS = ("情景", "scene", "scene_panel", "panel", "旋钮", "knob", "knob_switch")


@dataclass(frozen=True, slots=True)
class SensorSpec:
    """内部 sensor 投影规格."""

    component_id: str
    label: str
    device_class: str | None
    unit: str | None
    state_class: str | None = None
    icon: str | None = None


def sensor_specs(params: Mapping[str, Any]) -> dict[str, SensorSpec]:
    """返回当前 payload 可投影的明确 sensor 规格."""
    specs: dict[str, SensorSpec] = {}
    for key in REGISTRY_SENSOR_PROPS:
        if key not in params:
            continue
        spec = registry_sensor_spec(key)
        if spec is not None:
            specs[key] = spec
    for key, raw_spec in LEGACY_SENSOR_SPECS.items():
        specs[key] = SensorSpec(
            component_id=str(raw_spec["component_id"]),
            label=str(raw_spec["label"]),
            device_class=string_value(raw_spec["device_class"]),
            unit=string_value(raw_spec["unit"]),
            icon=string_value(raw_spec["icon"]),
        )
    return specs


def should_project_registry_sensor(
    key: str,
    component: ComponentInstanceModel | None,
) -> bool:
    """根据组件上下文过滤已知但暂不安全暴露的遥测属性。"""
    if (
        component is not None
        and to_category(component.category) == DALI_ENERGY_COMPONENT
        and key not in DALI_ENERGY_PROJECTED_PROPS
    ):
        return False
    return True


def registry_sensor_spec(prop: str) -> SensorSpec | None:
    """从 Yeelight IoT registry 派生 sensor 投影规格."""
    capability = property_capability(prop)
    spec = property_spec(prop)
    if capability is None or spec is None or not spec.readable:
        return None
    component_id, label = SENSOR_LABELS[prop]
    return SensorSpec(
        component_id=component_id,
        label=label,
        device_class=capability.device_class,
        unit=capability.unit or spec.unit,
        state_class=state_class_for_device_class(capability.device_class),
    )


def state_class_for_device_class(device_class: str | None) -> str | None:
    """返回 sensor 长期统计语义."""
    if device_class == "power":
        return "measurement"
    if device_class == "energy":
        return "total_increasing"
    return None


def device_name(
    device_payload: Mapping[str, Any], instance: HADeviceInstanceModel | None
) -> str | None:
    """获取设备名称，优先使用实例名称。"""
    if instance is not None and instance.name:
        return instance.name
    return string_value(device_payload.get("name"))


def projection_name(base_name: str | None, label: str | None) -> str | None:
    """返回投影实体名称（当前直接使用标签）。"""
    return label


def runtime_state(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
) -> dict[str, Any]:
    """合并载荷 params 与实例组件状态。"""
    merged = params(device_payload)
    merged.update(flatten_instance_state(instance))
    return merged


def params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """从 payload 中提取 params 字典."""
    raw_params = device_payload.get("params")
    return dict(raw_params) if isinstance(raw_params, Mapping) else {}


def component_for_prop(
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


def projection_available(
    base_available: bool,
    component: ComponentInstanceModel | None,
) -> bool:
    """计算投影实体的可用状态。"""
    if component is None:
        return base_available
    return bool(base_available and component.available)


def is_event_style_device(device_payload: Mapping[str, Any]) -> bool:
    """判断设备是否为情景面板、旋钮等事件输入设备。"""
    product_type = to_int(device_payload.get("product_type"))
    if product_type in EVENT_STYLE_PRODUCT_TYPES:
        return True

    product_model = device_payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        product = product_model.get("product")
        if isinstance(product, Mapping):
            category = to_category(product.get("category"))
            if category and matches_category(category, EVENT_INPUT_TOKENS):
                return True

    category = to_category(device_payload.get("category"))
    return bool(category) and matches_category(category, EVENT_INPUT_TOKENS)


def bool_value(value: Any, default: bool = False) -> bool:
    """安全布尔值转换。"""
    if value is None:
        return default
    return bool(value)


def string_value(value: Any) -> str | None:
    """安全字符串转换，空值返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "DALI_ENERGY_COMPONENT",
    "DALI_ENERGY_PROJECTED_PROPS",
    "EVENT_INPUT_TOKENS",
    "EVENT_STYLE_PRODUCT_TYPES",
    "LEGACY_SENSOR_SPECS",
    "REGISTRY_SENSOR_PROPS",
    "SENSOR_LABELS",
    "SensorSpec",
    "bool_value",
    "component_for_prop",
    "device_name",
    "is_event_style_device",
    "projection_available",
    "projection_name",
    "registry_sensor_spec",
    "runtime_state",
    "sensor_specs",
    "should_project_registry_sensor",
    "state_class_for_device_class",
    "string_value",
]
