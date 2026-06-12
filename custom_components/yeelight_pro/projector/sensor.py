"""Yeelight Pro sensor 投影模块.

将协调器运行时数据投影为 Home Assistant sensor 实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel, HAProductModel
from ..const import DEFAULT_HIDE_UNKNOWN_ENTITIES
from ..device_display import channel_name_label
from .common import (
    component_property_value,
    load_instance,
    load_product_model,
    payload_available,
    product_component,
)
from .device import project_payload_device_info
from .sensor_helpers import (
    device_payload_category,
    device_payload_id,
    is_event_style_device,
    is_event_style_component,
    is_unsupported_sensor_device,
    projection_available,
    projection_identity_has_token,
    projection_name,
    projection_property_keys,
    registry_sensor_spec,
    runtime_state,
    sensor_entity_category,
    sensor_spec_keys_for_instance,
    sensor_specs,
    should_project_registry_sensor,
)

_LOGGER = logging.getLogger(__name__)


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
        _log_sensor_skip(
            device_payload,
            prop_id=None,
            component=None,
            reason="unsupported_sensor_device",
        )
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
    if not occurrences:
        _log_sensor_missing_evidence(device_payload, instance, product_model, params)
    occurrence_counts = _property_occurrence_counts(occurrences)
    for key, component, value in occurrences:
        spec = specs.get(key) or registry_sensor_spec(key)
        if spec is None:
            _log_sensor_skip(
                device_payload,
                prop_id=key,
                component=component,
                reason="missing_sensor_spec",
            )
            continue
        if not should_project_registry_sensor(key, component):
            _log_sensor_skip(
                device_payload,
                prop_id=key,
                component=component,
                reason="registry_sensor_not_projectable",
            )
            continue
        entity_category = sensor_entity_category(key, component)
        if _blocks_event_style_sensor(event_style_device, component, entity_category):
            _log_sensor_skip(
                device_payload,
                prop_id=key,
                component=component,
                reason="event_style_component_owns_property",
            )
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

    return projections


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
            occurrences.append(
                (key, component, component_property_value(params, instance, component, key))
            )

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


def _log_sensor_missing_evidence(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
    params: Mapping[str, Any],
) -> None:
    """Log sensor-like payloads that lack documented sensor properties."""
    if not _LOGGER.isEnabledFor(logging.DEBUG) or not _looks_sensor_related(
        device_payload,
        instance,
        product_model,
    ):
        return
    _LOGGER.debug(
        "Skipping sensor projection: device_id=%s category=%s type=%s props=%s "
        "reason=missing_sensor_property_evidence",
        device_payload_id(device_payload),
        device_payload_category(device_payload),
        device_payload.get("type"),
        projection_property_keys(instance, product_model, params),
    )


def _log_sensor_skip(
    device_payload: Mapping[str, Any],
    *,
    prop_id: str | None,
    component: ComponentInstanceModel | None,
    reason: str,
) -> None:
    """Log why a known sensor property did not become a HA sensor entity."""
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    _LOGGER.debug(
        "Skipping sensor projection: device_id=%s component_id=%s category=%s "
        "component_category=%s prop_id=%s reason=%s",
        device_payload_id(device_payload),
        None if component is None else component.component_id,
        device_payload_category(device_payload),
        None if component is None else component.category,
        prop_id,
        reason,
    )


def _looks_sensor_related(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
) -> bool:
    """Return whether missing sensor evidence is worth a DEBUG breadcrumb."""
    return projection_identity_has_token(
        device_payload,
        instance,
        product_model,
        ("sensor",),
    )
