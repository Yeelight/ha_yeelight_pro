"""将 coordinator 运行时数据投影为 Home Assistant binary sensor 视图."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel, HAProductModel
from ..device_display import channel_name_label
from ..entity_category import entity_category_for_property
from ..utils import to_bool, to_category, to_int, to_str, matches_category
from .device import flatten_instance_state, project_payload_device_info
from .common import (
    load_product_model,
    payload_available,
    product_component,
    schema_backed_component_available,
)

# 事件型产品类型集合（仅暴露防拆状态的设备）
EVENT_STYLE_PRODUCT_TYPES = {128, 132}

# binary sensor 属性规格：key -> {component_id, label, device_class, icon, inverted}
BINARY_SENSOR_SPECS: dict[str, dict[str, str | None]] = {
    "mv": {
        "component_id": "motion",
        "label": "人体移动",
        "device_class": "motion",
        "icon": None,
        "inverted": None,
    },
    "dc": {
        "component_id": "door",
        "label": "门窗",
        "device_class": "door",
        "icon": None,
        "inverted": "true",
    },
    "alm": {
        "component_id": "tamper",
        "label": "防拆",
        "device_class": "tamper",
        "icon": None,
        "inverted": None,
    },
    "bc": {
        "component_id": "battery_chargeable",
        "label": "电池可充电",
        "device_class": None,
        "icon": "mdi:battery-check",
        "inverted": None,
    },
    "bcg": {
        "component_id": "battery_charging",
        "label": "电池充电",
        "device_class": "battery_charging",
        "icon": None,
        "inverted": None,
    },
}

# 情景/面板类设备类别 token
_SCENE_CATEGORY_TOKENS = (
    "情景",
    "scene",
    "scene_panel",
    "panel",
    "旋钮",
    "knob",
    "knob_switch",
)


@dataclass(slots=True)
class HABinarySensorProjection:
    """投影后的 Home Assistant binary sensor 视图."""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    is_on: bool | None
    device_class: str | None
    device_info: dict[str, Any] | None
    icon: str | None = None
    entity_category: str | None = None


def project_binary_sensors(
    device_payload: Mapping[str, Any], *, domain: str
) -> list[HABinarySensorProjection]:
    """将 coordinator payload 投影为一个或多个 binary sensor."""
    instance = _load_instance(device_payload)
    product_model = load_product_model(device_payload)
    params = _runtime_state(device_payload, instance)
    device_info = project_payload_device_info(device_payload, instance)
    device_id = str(device_payload.get("device_id", "unknown"))
    base_available = payload_available(device_payload, instance)
    event_style_device = _is_event_style_device(device_payload)

    projections: list[HABinarySensorProjection] = []
    occurrences = _binary_sensor_property_occurrences(instance, product_model, params)
    occurrence_counts = _property_occurrence_counts(occurrences)
    for key, component, raw_value in occurrences:
        spec = BINARY_SENSOR_SPECS.get(key)
        if spec is None:
            continue
        entity_category = entity_category_for_property(key)
        if event_style_device and entity_category is None:
            continue

        is_on = None if raw_value is None else to_bool(raw_value)
        if is_on is not None and spec.get("inverted") == "true":
            is_on = not is_on

        schema_component = (
            product_component(product_model, component.component_id)
            if component is not None
            else None
        )
        scoped = component is not None and occurrence_counts.get(key, 0) > 1
        component_id = _scoped_component_id(
            str(spec["component_id"]),
            component,
            scoped=scoped,
        )
        projections.append(
            HABinarySensorProjection(
                component_id=component_id,
                unique_id=f"{domain}_{device_id}_{component_id}",
                name=_scoped_projection_name(component, spec["label"], scoped=scoped),
                available=_projection_available(
                    base_available,
                    component,
                    schema_component=schema_component,
                ),
                is_on=is_on,
                device_class=to_str(spec["device_class"]),
                device_info=device_info,
                icon=to_str(spec["icon"]),
                entity_category=entity_category,
            )
        )

    return projections


def _binary_sensor_property_occurrences(
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
    params: Mapping[str, Any],
) -> list[tuple[str, ComponentInstanceModel | None, Any]]:
    """Return binary sensor properties without collapsing component scope."""
    if instance is None:
        return [
            (key, None, params.get(key))
            for key in _binary_sensor_keys(None, None, params)
        ]

    occurrences: list[tuple[str, ComponentInstanceModel | None, Any]] = []
    scoped_keys: set[str] = set()
    for component in instance.components:
        component_keys = {str(key): None for key in component.state}
        schema_component = product_component(product_model, component.component_id)
        if schema_component is not None:
            component_keys.update(
                {prop.prop_id: None for prop in schema_component.properties}
            )
        for key in _binary_sensor_keys(None, None, component_keys):
            scoped_keys.add(key)
            occurrences.append((key, component, component.state.get(key)))

    for key in _binary_sensor_keys(None, None, params):
        if key not in scoped_keys:
            occurrences.append((key, None, params.get(key)))
    return occurrences


def _property_occurrence_counts(
    occurrences: list[tuple[str, ComponentInstanceModel | None, Any]],
) -> dict[str, int]:
    """Return how many times each property appears across components."""
    counts: dict[str, int] = {}
    for key, _component, _value in occurrences:
        counts[key] = counts.get(key, 0) + 1
    return counts


def _scoped_component_id(
    base_component_id: str,
    component: ComponentInstanceModel | None,
    *,
    scoped: bool,
) -> str:
    """Prefix component id only when multiple components expose the same property."""
    if not scoped or component is None:
        return base_component_id
    return f"{component.component_id}_{base_component_id}"


def _scoped_projection_name(
    component: ComponentInstanceModel | None,
    label: str | None,
    *,
    scoped: bool,
) -> str | None:
    """Return readable names for duplicate per-component binary sensors."""
    if not scoped:
        return _projection_name(None, label)
    channel = channel_name_label(index=None, component=component)
    if channel and label:
        return f"{channel} {label}"
    return label or channel


def _binary_sensor_keys(
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
    params: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return binary sensor properties from runtime state and product schema."""
    keys = set(params)
    if instance is not None:
        keys.update(
            str(key)
            for component in instance.components
            for key in component.state
        )
    if product_model is not None:
        keys.update(
            prop.prop_id
            for component in product_model.components
            for prop in component.properties
        )
    return tuple(key for key in BINARY_SENSOR_SPECS if key in keys)


def _load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从 payload 中加载设备实例模型."""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _projection_name(base_name: str | None, label: str | None) -> str | None:
    """返回投影名称，当前直接使用标签."""
    return label


def _is_event_style_device(device_payload: Mapping[str, Any]) -> bool:
    """判断是否为事件型设备（情景面板/旋钮等）."""
    product_type = to_int(device_payload.get("product_type"))
    if product_type in EVENT_STYLE_PRODUCT_TYPES:
        return True

    product_model = device_payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        product = product_model.get("product")
        if isinstance(product, Mapping):
            category = to_category(product.get("category"))
            if category and matches_category(category, _SCENE_CATEGORY_TOKENS):
                return True

    category = to_category(device_payload.get("category"))
    return bool(category) and matches_category(category, _SCENE_CATEGORY_TOKENS)


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """提取 payload 中的 params 字段."""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _runtime_state(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
) -> dict[str, Any]:
    """合并 payload params 与实例组件状态."""
    merged = _params(device_payload)
    merged.update(flatten_instance_state(instance))
    return merged


def _projection_available(
    base_available: bool,
    component: ComponentInstanceModel | None,
    *,
    schema_component: Any | None = None,
) -> bool:
    """计算投影可用性：基础可用性与组件可用性的交集."""
    return schema_backed_component_available(
        base_available,
        component,
        schema_component=schema_component,
    )
