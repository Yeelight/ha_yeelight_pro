"""Yeelight Pro sensor 投影模块.

将协调器运行时数据投影为 Home Assistant sensor 实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel, HAProductModel
from ..capabilities.filter import (
    should_project_unknown_property,
    unknown_sensor_component_id,
    unknown_sensor_name,
)
from ..const import DEFAULT_HIDE_UNKNOWN_ENTITIES
from ..device_display import channel_name_label
from .common import load_instance, load_product_model, payload_available, product_component
from .device import project_payload_device_info
from .sensor_helpers import (
    is_event_style_device,
    is_event_style_component,
    is_unsupported_sensor_device,
    projection_available,
    projection_name,
    registry_sensor_spec,
    runtime_state,
    sensor_entity_category,
    sensor_spec_keys_for_instance,
    sensor_specs,
    should_project_registry_sensor,
)


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
    state_class: str | None
    device_info: dict[str, Any] | None
    icon: str | None = None
    entity_category: str | None = None


def project_sensors(
    device_payload: Mapping[str, Any],
    *,
    domain: str,
    hide_unknown_entities: bool | None = None,
) -> list[HASensorProjection]:
    """将协调器载荷投影为一组 sensor 视图。"""
    if hide_unknown_entities is None:
        hide_unknown_entities = bool(
            device_payload.get("hide_unknown_entities", DEFAULT_HIDE_UNKNOWN_ENTITIES)
        )
    if is_unsupported_sensor_device(device_payload):
        return []

    instance = load_instance(device_payload)
    product_model = load_product_model(device_payload)
    params = runtime_state(device_payload, instance)
    device_info = project_payload_device_info(device_payload, instance)
    device_id = str(device_payload.get("device_id", "unknown"))
    base_available = payload_available(device_payload, instance)
    event_style_device = is_event_style_device(device_payload)

    projections: list[HASensorProjection] = []
    specs = sensor_specs(params)
    occurrences = _sensor_property_occurrences(instance, product_model, params)
    occurrence_counts = _property_occurrence_counts(occurrences)
    for key, component, value in occurrences:
        spec = specs.get(key) or registry_sensor_spec(key)
        if spec is None:
            continue
        if not should_project_registry_sensor(key, component):
            continue
        entity_category = sensor_entity_category(key, component)
        if _blocks_event_style_sensor(event_style_device, component, entity_category):
            continue
        schema_component = (
            product_component(product_model, component.component_id)
            if component is not None
            else None
        )
        scoped = component is not None and occurrence_counts.get(key, 0) > 1
        component_id = _scoped_component_id(spec.component_id, component, scoped=scoped)
        projections.append(
            HASensorProjection(
                component_id=component_id,
                unique_id=f"{domain}_{device_id}_{component_id}",
                name=_scoped_projection_name(component, spec.label, scoped=scoped),
                available=projection_available(
                    base_available,
                    component,
                    schema_component=schema_component,
                ),
                native_value=value,
                device_class=spec.device_class,
                native_unit_of_measurement=spec.unit,
                state_class=spec.state_class,
                device_info=device_info,
                icon=spec.icon,
                entity_category=entity_category,
            )
        )

    projected_keys = _projected_sensor_keys(occurrences)
    for key, value in params.items():
        if value is None:
            continue
        decision = should_project_unknown_property(
            key,
            value,
            device_payload,
            platform="sensor",
            hide_unknown_entities=hide_unknown_entities,
        )
        if not decision.allowed or key in projected_keys:
            continue
        component_id = unknown_sensor_component_id(key)
        projections.append(
            HASensorProjection(
                component_id=component_id,
                unique_id=f"{domain}_{device_id}_{component_id}",
                name=unknown_sensor_name(key),
                available=base_available,
                native_value=value,
                device_class=None,
                native_unit_of_measurement=None,
                state_class=None,
                device_info=device_info,
                icon="mdi:help-circle-outline",
            )
        )

    return projections


def _projected_sensor_keys(
    occurrences: list[tuple[str, ComponentInstanceModel | None, Any]],
) -> set[str]:
    """Return all registry-backed sensor keys already handled by schema/runtime."""
    return {key for key, _component, _value in occurrences}


def _sensor_property_occurrences(
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
    params: Mapping[str, Any],
) -> list[tuple[str, ComponentInstanceModel | None, Any]]:
    """Return sensor properties with component scope preserved when available."""
    if instance is None:
        return [
            (key, None, params.get(key))
            for key in sensor_spec_keys_for_instance(None, None, params)
        ]

    occurrences: list[tuple[str, ComponentInstanceModel | None, Any]] = []
    seen: set[tuple[str | None, str]] = set()
    for component in instance.components:
        component_keys = {str(key): None for key in component.state}
        schema_component = product_component(product_model, component.component_id)
        if schema_component is not None:
            component_keys.update(
                {prop.prop_id: None for prop in schema_component.properties}
            )
        for key in sensor_spec_keys_for_instance(None, None, component_keys):
            seen.add((component.component_id, key))
            occurrences.append((key, component, component.state.get(key)))

    scoped_keys = {key for _component_id, key in seen}
    for key in sensor_spec_keys_for_instance(None, None, params):
        if key not in scoped_keys:
            occurrences.append((key, None, params.get(key)))
    return occurrences


def _blocks_event_style_sensor(
    event_style_device: bool,
    component: ComponentInstanceModel | None,
    entity_category: str | None,
) -> bool:
    """Return true when an event-input component would leak as a normal sensor."""
    return entity_category is None and (
        (event_style_device and component is None) or is_event_style_component(component)
    )


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
    """Prefix component id only when needed to avoid multi-component collisions."""
    if not scoped or component is None:
        return base_component_id
    return f"{component.component_id}_{base_component_id}"


def _scoped_projection_name(
    component: ComponentInstanceModel | None,
    label: str | None,
    *,
    scoped: bool,
) -> str | None:
    """Return a readable name for duplicate per-component telemetry entities."""
    if not scoped:
        return projection_name(None, label)
    channel = channel_name_label(index=None, component=component)
    if channel and label:
        return f"{channel} {label}"
    return label or channel
