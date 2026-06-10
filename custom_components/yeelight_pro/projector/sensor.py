"""Yeelight Pro sensor 投影模块.

将协调器运行时数据投影为 Home Assistant sensor 实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..capabilities.filter import (
    should_project_unknown_property,
    unknown_sensor_component_id,
    unknown_sensor_name,
)
from ..const import DEFAULT_HIDE_UNKNOWN_ENTITIES
from .common import load_instance
from .device import project_payload_device_info
from .sensor_helpers import (
    bool_value,
    component_for_prop,
    device_name,
    is_event_style_device,
    projection_available,
    projection_name,
    runtime_state,
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


def project_sensors(
    device_payload: Mapping[str, Any],
    *,
    domain: str,
    hide_unknown_entities: bool | None = None,
) -> list[HASensorProjection]:
    """将协调器载荷投影为一组 sensor 视图。"""
    if is_event_style_device(device_payload):
        return []

    if hide_unknown_entities is None:
        hide_unknown_entities = bool(
            device_payload.get("hide_unknown_entities", DEFAULT_HIDE_UNKNOWN_ENTITIES)
        )

    instance = load_instance(device_payload)
    params = runtime_state(device_payload, instance)
    device_info = project_payload_device_info(device_payload, instance)
    base_name = device_name(device_payload, instance)
    device_id = str(device_payload.get("device_id", "unknown"))
    base_available = bool_value(device_payload.get("online"), default=False)
    if instance is not None:
        base_available = bool(instance.online)

    projections: list[HASensorProjection] = []
    specs = sensor_specs(params)
    for key, spec in specs.items():
        if key not in params:
            continue
        component = component_for_prop(instance, key)
        if not should_project_registry_sensor(key, component):
            continue
        projections.append(
            HASensorProjection(
                component_id=spec.component_id,
                unique_id=f"{domain}_{device_id}_{spec.component_id}",
                name=projection_name(base_name, spec.label),
                available=projection_available(base_available, component),
                native_value=params.get(key),
                device_class=spec.device_class,
                native_unit_of_measurement=spec.unit,
                state_class=spec.state_class,
                device_info=device_info,
                icon=spec.icon,
            )
        )

    projected_keys = set(specs)
    for key, value in params.items():
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
