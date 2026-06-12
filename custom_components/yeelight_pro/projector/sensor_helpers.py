"""Sensor-specific helper functions for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import (
    ComponentInstanceModel,
    ComponentModel,
    HADeviceInstanceModel,
    HAProductModel,
)
from ..utils import matches_category, to_category
from .common import schema_backed_component_available
from .device import flatten_instance_state
from .event_input import (
    EVENT_INPUT_CATEGORIES,
    EVENT_STYLE_PRODUCT_TYPES,
    is_event_input_component_context,
    is_event_input_device,
)
from .sensor_metadata import (
    DALI_ENERGY_COMPONENT,
    DALI_ENERGY_PROJECTED_PROPS,
    REGISTRY_SENSOR_PROPS,
    SENSOR_LABELS,
    SensorSpec,
    icon_for_property,
    registry_sensor_spec,
    sensor_entity_category,
    should_project_registry_sensor,
    state_class_for_device_class,
)

UNSUPPORTED_SENSOR_TOKENS = ("vacuum",)


def sensor_specs(params: Mapping[str, Any]) -> dict[str, SensorSpec]:
    """返回当前 payload 可投影的明确 sensor 规格."""
    specs: dict[str, SensorSpec] = {}
    for key in REGISTRY_SENSOR_PROPS:
        if key not in params:
            continue
        spec = registry_sensor_spec(key)
        if spec is not None:
            specs[key] = spec
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
        key for key in REGISTRY_SENSOR_PROPS if key in keys
    )


def device_payload_id(device_payload: Mapping[str, Any]) -> str | None:
    """Return a stable non-secret device id for projection diagnostics."""
    value = device_payload.get("device_id")
    return str(value) if value is not None else None


def device_payload_category(device_payload: Mapping[str, Any]) -> Any:
    """Return category metadata without inspecting user-provided names."""
    return device_payload.get("iot_category") or device_payload.get("category")


def projection_property_keys(
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
    params: Mapping[str, Any],
) -> list[str]:
    """Return property keys only; values may contain user data and stay out of logs."""
    keys = {str(key) for key in params}
    if instance is not None:
        keys.update(
            str(key)
            for component in instance.components
            for key in component.state
        )
    if product_model is not None:
        keys.update(
            str(prop.prop_id)
            for component in product_model.components
            for prop in component.properties
        )
    return sorted(keys)


def projection_identity_has_token(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
    tokens: tuple[str, ...],
) -> bool:
    """Return whether device/component identity contains a documented token."""
    values: list[Any] = [
        device_payload.get("iot_category"),
        device_payload.get("category"),
        device_payload.get("type"),
        device_payload.get("component_id"),
    ]
    if instance is not None:
        values.extend(component.category for component in instance.components)
    if product_model is not None:
        values.append(product_model.product.category)
        values.extend(component.category for component in product_model.components)
    return any(
        any(token in str(value).lower() for token in tokens)
        for value in values
        if value is not None
    )


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
    return is_event_input_device(device_payload)


def is_event_style_component(component: ComponentInstanceModel | None) -> bool:
    """Return true when this specific component is an event input."""
    if component is None:
        return False
    return is_event_input_component_context(component.category, component.component_id)


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
    "EVENT_INPUT_CATEGORIES",
    "EVENT_STYLE_PRODUCT_TYPES",
    "REGISTRY_SENSOR_PROPS",
    "SENSOR_LABELS",
    "SensorSpec",
    "bool_value",
    "component_for_prop",
    "device_payload_category",
    "device_payload_id",
    "device_name",
    "is_event_style_device",
    "is_event_style_component",
    "is_unsupported_sensor_device",
    "icon_for_property",
    "projection_available",
    "projection_identity_has_token",
    "projection_name",
    "projection_property_keys",
    "sensor_spec_keys_for_instance",
    "registry_sensor_spec",
    "runtime_state",
    "sensor_specs",
    "sensor_entity_category",
    "should_project_registry_sensor",
    "state_class_for_device_class",
    "string_value",
]
