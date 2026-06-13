"""将 coordinator 运行时数据投影为 Home Assistant binary sensor 视图."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel, HAProductModel
from ..device_display import channel_name_label
from ..entity_category import entity_category_for_property
from ..identity import payload_entity_unique_id_prefix
from ..utils import to_bool, to_str
from .device import flatten_instance_state, project_payload_device_info
from .event_input import is_event_input_device
from .sensor_helpers import (
    device_payload_category,
    device_payload_id,
    is_event_style_component,
    projection_identity_has_token,
    projection_property_keys,
)
from .common import (
    component_property_value,
    load_product_model,
    payload_available,
    product_component,
    schema_backed_component_available,
)

_LOGGER = logging.getLogger(__name__)

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
    "aco": {
        "component_id": "ac_online",
        "label": "空调在线",
        "device_class": None,
        "icon": "mdi:air-conditioner",
        "inverted": None,
    },
    "rs": {
        "component_id": "route_calibrated",
        "label": "行程已校准",
        "device_class": None,
        "icon": "mdi:ray-start-end",
        "inverted": None,
    },
    "trs": {
        "component_id": "tilt_route_calibrated",
        "label": "调光行程已校准",
        "device_class": None,
        "icon": "mdi:ray-start-end",
        "inverted": None,
    },
    "slisaon_rdy": {
        "component_id": "slisaon_ready",
        "label": "支持闪断",
        "device_class": None,
        "icon": "mdi:flash",
        "inverted": None,
    },
    "run_speed_rdy": {
        "component_id": "run_speed_ready",
        "label": "支持运行速度",
        "device_class": None,
        "icon": "mdi:speedometer",
        "inverted": None,
    },
}
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
    unique_id_prefix = payload_entity_unique_id_prefix(device_payload, domain=domain)
    base_available = payload_available(device_payload, instance)
    event_style_device = is_event_input_device(device_payload)

    projections: list[HABinarySensorProjection] = []
    occurrences = _binary_sensor_property_occurrences(instance, product_model, params)
    if not occurrences:
        _log_binary_sensor_missing_evidence(
            device_payload,
            instance,
            product_model,
            params,
        )
    occurrence_counts = _property_occurrence_counts(occurrences)
    for key, component, raw_value in occurrences:
        spec = BINARY_SENSOR_SPECS.get(key)
        if spec is None:
            _log_binary_sensor_skip(
                device_payload,
                prop_id=key,
                component=component,
                reason="missing_binary_sensor_spec",
            )
            continue
        entity_category = entity_category_for_property(key)
        if _blocks_event_style_binary_sensor(
            event_style_device,
            component,
            entity_category,
        ):
            _log_binary_sensor_skip(
                device_payload,
                prop_id=key,
                component=component,
                reason="event_style_component_owns_property",
            )
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
                unique_id=f"{unique_id_prefix}_{device_id}_{component_id}",
                name=_scoped_projection_name(component, spec["label"], scoped=scoped),
                available=schema_backed_component_available(
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
            occurrences.append(
                (key, component, component_property_value(params, instance, component, key))
            )

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


def _blocks_event_style_binary_sensor(
    event_style_device: bool,
    component: ComponentInstanceModel | None,
    entity_category: str | None,
) -> bool:
    """Return true when an event-input component would leak as a binary sensor."""
    return entity_category is None and (
        (event_style_device and component is None) or is_event_style_component(component)
    )


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


def _log_binary_sensor_missing_evidence(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
    params: Mapping[str, Any],
) -> None:
    """Log sensor-like payloads with no documented binary sensor properties."""
    if not _LOGGER.isEnabledFor(logging.DEBUG) or not _looks_binary_sensor_related(
        device_payload,
        instance,
        product_model,
    ):
        return
    _LOGGER.debug(
        "Skipping binary_sensor projection: device_id=%s category=%s type=%s props=%s "
        "reason=missing_binary_sensor_property_evidence",
        device_payload_id(device_payload),
        device_payload_category(device_payload),
        device_payload.get("type"),
        projection_property_keys(instance, product_model, params),
    )


def _log_binary_sensor_skip(
    device_payload: Mapping[str, Any],
    *,
    prop_id: str | None,
    component: ComponentInstanceModel | None,
    reason: str,
) -> None:
    """Log why a binary sensor property did not become a HA entity."""
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    _LOGGER.debug(
        "Skipping binary_sensor projection: device_id=%s component_id=%s "
        "category=%s component_category=%s prop_id=%s reason=%s",
        device_payload_id(device_payload),
        None if component is None else component.component_id,
        device_payload_category(device_payload),
        None if component is None else component.category,
        prop_id,
        reason,
    )


def _looks_binary_sensor_related(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
) -> bool:
    """Return whether missing binary evidence deserves a DEBUG breadcrumb."""
    return projection_identity_has_token(
        device_payload,
        instance,
        product_model,
        ("sensor", "contact", "human", "motion", "alarm"),
    )
