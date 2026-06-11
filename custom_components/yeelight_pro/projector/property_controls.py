"""Project writable Yeelight schema properties into HA control helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import (
    ComponentInstanceModel,
    HADeviceInstanceModel,
    PropertyModel,
)
from ..utils import to_float
from .common import NumericRange, load_instance
from .device import project_payload_device_info
from .property_control_common import (
    control_available,
    control_key,
    control_name,
    entity_category_for_property,
    is_writable_auxiliary_bool_property,
    is_writable_auxiliary_property,
    number_icon,
    schema_properties,
    select_icon,
    select_options,
    switch_icon,
)


@dataclass(frozen=True, slots=True)
class HASelectOption:
    """One user-facing select option mapped to the raw Yeelight code."""

    value: Any
    label: str


@dataclass(frozen=True, slots=True)
class HANumberControlProjection:
    """Projected writable numeric property."""

    component_id: str
    prop_id: str
    unique_id: str
    name: str | None
    available: bool
    value: float | None
    native_range: NumericRange
    unit: str | None
    control_key: str
    device_info: dict[str, Any] | None
    icon: str | None = None
    entity_category: str | None = None


@dataclass(frozen=True, slots=True)
class HASelectControlProjection:
    """Projected writable enum property."""

    component_id: str
    prop_id: str
    unique_id: str
    name: str | None
    available: bool
    value: Any
    options: tuple[HASelectOption, ...]
    control_key: str
    device_info: dict[str, Any] | None
    icon: str | None = None
    entity_category: str | None = None


@dataclass(frozen=True, slots=True)
class HASwitchControlProjection:
    """Projected writable boolean property that is not owned by a main entity."""

    component_id: str
    prop_id: str
    unique_id: str
    name: str | None
    available: bool
    is_on: bool
    control_key: str
    device_info: dict[str, Any] | None
    icon: str | None = None
    entity_category: str | None = None


def project_number_controls(
    device_payload: Mapping[str, Any], *, domain: str
) -> list[HANumberControlProjection]:
    """Project writable valueRange properties that are not owned by main entities."""
    instance = load_instance(device_payload)
    if instance is None:
        return []
    return [
        projection
        for component in instance.components
        for prop in schema_properties(device_payload, component)
        if (projection := _project_number(device_payload, instance, component, prop, domain=domain))
        is not None
    ]


def project_select_controls(
    device_payload: Mapping[str, Any], *, domain: str
) -> list[HASelectControlProjection]:
    """Project writable valueList properties that are not owned by main entities."""
    instance = load_instance(device_payload)
    if instance is None:
        return []
    return [
        projection
        for component in instance.components
        for prop in schema_properties(device_payload, component)
        if (projection := _project_select(device_payload, instance, component, prop, domain=domain))
        is not None
    ]


def project_switch_controls(
    device_payload: Mapping[str, Any], *, domain: str
) -> list[HASwitchControlProjection]:
    """Project documented writable boolean properties into config switches."""
    instance = load_instance(device_payload)
    if instance is None:
        return []
    return [
        projection
        for component in instance.components
        for prop in schema_properties(device_payload, component)
        if (
            projection := _project_switch(
                device_payload,
                instance,
                component,
                prop,
                domain=domain,
            )
        )
        is not None
    ]


def _project_number(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    prop: PropertyModel,
    *,
    domain: str,
) -> HANumberControlProjection | None:
    if not is_writable_auxiliary_property(prop):
        return None
    if prop.value_range is None or prop.value_list:
        return None

    numeric_range = NumericRange(
        min=prop.value_range.min,
        max=prop.value_range.max,
        step=prop.value_range.step,
    )
    return HANumberControlProjection(
        component_id=f"{component.component_id}_{prop.prop_id}_number",
        prop_id=prop.prop_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}_{prop.prop_id}_number",
        name=control_name(component, prop, device_payload=device_payload),
        available=control_available(device_payload, instance, component),
        value=to_float(component.state.get(prop.prop_id)),
        native_range=numeric_range,
        unit=prop.unit,
        control_key=control_key(instance, component.component_id, prop.prop_id),
        device_info=project_payload_device_info(device_payload, instance),
        icon=number_icon(prop),
        entity_category=entity_category_for_property(prop.prop_id),
    )


def _project_select(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    prop: PropertyModel,
    *,
    domain: str,
) -> HASelectControlProjection | None:
    if not is_writable_auxiliary_property(prop):
        return None
    if not prop.value_list:
        return None
    options = tuple(select_options(prop.value_list, HASelectOption))
    if not options:
        return None

    return HASelectControlProjection(
        component_id=f"{component.component_id}_{prop.prop_id}_select",
        prop_id=prop.prop_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}_{prop.prop_id}_select",
        name=control_name(component, prop, device_payload=device_payload),
        available=control_available(device_payload, instance, component),
        value=component.state.get(prop.prop_id),
        options=options,
        control_key=control_key(instance, component.component_id, prop.prop_id),
        device_info=project_payload_device_info(device_payload, instance),
        icon=select_icon(prop),
        entity_category=entity_category_for_property(prop.prop_id),
    )


def _project_switch(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    prop: PropertyModel,
    *,
    domain: str,
) -> HASwitchControlProjection | None:
    if not is_writable_auxiliary_bool_property(prop):
        return None

    return HASwitchControlProjection(
        component_id=f"{component.component_id}_{prop.prop_id}_switch",
        prop_id=prop.prop_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}_{prop.prop_id}_switch",
        name=control_name(component, prop, device_payload=device_payload),
        available=control_available(device_payload, instance, component),
        is_on=bool(component.state.get(prop.prop_id, prop.default or False)),
        control_key=control_key(instance, component.component_id, prop.prop_id),
        device_info=project_payload_device_info(device_payload, instance),
        icon=switch_icon(prop),
        entity_category=entity_category_for_property(prop.prop_id),
    )


__all__ = [
    "HANumberControlProjection",
    "HASelectControlProjection",
    "HASelectOption",
    "HASwitchControlProjection",
    "project_number_controls",
    "project_select_controls",
    "project_switch_controls",
]
