"""Sensor-specific helper functions for Yeelight Pro projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import (
    ComponentInstanceModel,
    ComponentModel,
    HADeviceInstanceModel,
    HAProductModel,
)
from ..capabilities.registry import property_capability, property_spec
from ..entity_category import (
    ENTITY_CATEGORY_DIAGNOSTIC,
    entity_category_for_property,
)
from ..utils import matches_category, to_category, to_int
from .common import schema_backed_component_available
from .device import flatten_instance_state

SENSOR_LABELS = {
    "t": ("temperature", "温度"),
    "temp": ("temperature", "温度"),
    "h": ("humidity", "湿度"),
    "luminance": ("illuminance", "光照"),
    "curp": ("current_power", "当前功率"),
    "iec": ("energy_consumption", "阶段电量"),
    "ap": ("active_power", "有功功率"),
    "ae": ("active_energy", "总有功"),
    "bl": ("battery", "电量"),
    "acct": ("current_temperature", "当前温度"),
    "rfhct": ("floor_heating_temperature", "地暖温度"),
    "o": ("online_status", "在线状态"),
    "pl": ("physical_link", "物理连接"),
    "lf": ("uptime", "运行时间"),
    "fm": ("free_memory", "剩余内存"),
    "cpt": ("connectivity_protocol", "接入协议"),
    "li": ("indicator_switch", "指示灯配置"),
    "lc": ("lan_control", "局域网控制配置"),
    "rd": ("reverse_direction", "电机方向配置"),
    "blp": ("backlight_power", "背光配置"),
    "ep": ("event_priority", "事件优先级"),
    "st": ("short_timer", "短计时配置"),
    "rt": ("repeat_timer", "重复计时配置"),
    "ot": ("operating_time", "运行时长"),
    "sys_s": ("system_starts", "系统启动次数"),
    "esv": ("external_supply_voltage", "外部供电电压"),
    "esvf": ("external_supply_frequency", "外部供电频率"),
    "ocp": ("output_current_percent", "输出电流百分比"),
    "lsot": ("light_source_on_time", "光源点亮时长"),
    "lsv": ("light_source_voltage", "光源电压"),
    "lsc": ("light_source_current", "光源电流"),
    "pf": ("power_factor", "功率因数"),
}
REGISTRY_SENSOR_PROPS = frozenset(SENSOR_LABELS)
DALI_ENERGY_COMPONENT = "dali energy"
DALI_ENERGY_PROJECTED_PROPS = frozenset({
    "ae",
    "ap",
    "esv",
    "esvf",
    "lsc",
    "lsot",
    "lsv",
    "ocp",
    "ot",
    "pf",
    "sys_s",
    "temp",
})
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
UNSUPPORTED_SENSOR_TOKENS = ("vacuum",)


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


def sensor_spec_keys_for_instance(
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
    params: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return known sensor props from runtime state and canonical component schema."""
    keys = set(params)
    if instance is not None:
        keys.update(_component_state_keys(instance))
    if product_model is not None:
        keys.update(_product_property_keys(product_model))
    return tuple(
        key for key in REGISTRY_SENSOR_PROPS | set(LEGACY_SENSOR_SPECS) if key in keys
    )


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


def sensor_entity_category(
    prop: str,
    component: ComponentInstanceModel | None,
) -> str | None:
    """返回 sensor 的 HA 分类。"""
    category = entity_category_for_property(prop)
    if category is not None:
        return category
    if component is not None and to_category(component.category) == DALI_ENERGY_COMPONENT:
        return ENTITY_CATEGORY_DIAGNOSTIC
    return None


def registry_sensor_spec(prop: str) -> SensorSpec | None:
    """从 Yeelight IoT registry 派生 sensor 投影规格."""
    capability = property_capability(prop)
    spec = property_spec(prop)
    if spec is None or not spec.readable:
        return None
    component_id, label = SENSOR_LABELS[prop]
    if prop == "temp":
        component_id = "internal_temperature"
        label = "内部温度"
    return SensorSpec(
        component_id=component_id,
        label=label,
        device_class=capability.device_class if capability is not None else None,
        unit=(capability.unit if capability is not None else None) or spec.unit,
        state_class=state_class_for_device_class(
            capability.device_class if capability is not None else None
        ),
        icon=icon_for_property(prop),
    )


def state_class_for_device_class(device_class: str | None) -> str | None:
    """返回 sensor 长期统计语义."""
    if device_class == "power":
        return "measurement"
    if device_class == "energy":
        return "total_increasing"
    if device_class in {"temperature", "humidity", "illuminance", "battery"}:
        return "measurement"
    return None


def icon_for_property(prop: str) -> str | None:
    """返回无标准 device_class 属性的图标。"""
    return {
        "bc": "mdi:battery-check",
        "bcg": "mdi:battery-charging",
        "cpt": "mdi:access-point-network",
        "ep": "mdi:ray-start-arrow",
        "fm": "mdi:memory",
        "lc": "mdi:lan-connect",
        "lf": "mdi:timer-outline",
        "li": "mdi:led-on",
        "o": "mdi:connection",
        "ot": "mdi:timer-outline",
        "pl": "mdi:ethernet",
        "rd": "mdi:swap-horizontal",
        "rt": "mdi:timer-sync-outline",
        "st": "mdi:timer-cog-outline",
        "sys_s": "mdi:restart",
    }.get(prop)


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
    product_model: HAProductModel | None,
    prop_key: str,
) -> ComponentInstanceModel | None:
    """查找包含指定属性键的组件。"""
    if instance is None:
        return None
    for component in instance.components:
        if prop_key in component.state:
            return component
    component_ids = _product_component_ids_for_prop(product_model, prop_key)
    for component in instance.components:
        if component.component_id in component_ids:
            return component
    return None


def projection_available(
    base_available: bool,
    component: ComponentInstanceModel | None,
    *,
    schema_component: ComponentModel | None = None,
) -> bool:
    """计算投影实体的可用状态。"""
    return schema_backed_component_available(
        base_available,
        component,
        schema_component=schema_component,
    )


def _component_state_keys(instance: HADeviceInstanceModel) -> set[str]:
    """Return all property keys currently present in component state."""
    return {
        str(key)
        for component in instance.components
        for key in component.state
    }


def _product_property_keys(product_model: HAProductModel) -> set[str]:
    """Return schema-backed property keys from canonical component metadata."""
    return {
        key
        for component in product_model.components
        for key in _component_property_keys(component)
    }


def _product_component_ids_for_prop(
    product_model: HAProductModel | None,
    prop_key: str,
) -> set[str]:
    """Return product component ids that declare the given property."""
    if product_model is None:
        return set()
    return {
        component.component_id
        for component in product_model.components
        if any(prop.prop_id == prop_key for prop in component.properties)
    }


def _component_property_keys(component: Any) -> set[str]:
    """Return schema property ids when the component instance carries them."""
    properties = getattr(component, "properties", None)
    return {
        prop_id
        for prop in properties or []
        if (prop_id := string_value(getattr(prop, "prop_id", None))) is not None
    }


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


def is_unsupported_sensor_device(device_payload: Mapping[str, Any]) -> bool:
    """判断是否为无易来文档支撑且不能 fallback 成传感器的设备。"""
    values = (
        device_payload.get("type"),
        device_payload.get("category"),
        device_payload.get("iot_category"),
        device_payload.get("component_id"),
        device_payload.get("component"),
        device_payload.get("component_name"),
    )
    return any(matches_category(to_category(value), UNSUPPORTED_SENSOR_TOKENS) for value in values)


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
    "is_unsupported_sensor_device",
    "icon_for_property",
    "projection_available",
    "projection_name",
    "sensor_spec_keys_for_instance",
    "registry_sensor_spec",
    "runtime_state",
    "sensor_specs",
    "sensor_entity_category",
    "should_project_registry_sensor",
    "state_class_for_device_class",
    "string_value",
]
