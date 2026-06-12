"""Project writable Yeelight schema properties into HA control helpers."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping

from ..canonical.models import (
    ComponentInstanceModel,
    HADeviceInstanceModel,
    PropertyModel,
)
from ..utils import to_float
from ..utils import to_bool
from .common import NumericRange, component_property_value, load_instance
from .device import project_payload_device_info
from .property_control_common import (
    auxiliary_bool_property_skip_reason,
    auxiliary_property_skip_reason,
    control_available,
    control_key,
    control_name,
    control_unit,
    control_value_list,
    control_value_range,
    entity_category_for_property,
    is_writable_auxiliary_bool_property,
    is_writable_auxiliary_property,
    number_icon,
    schema_properties,
    select_icon,
    select_options,
    switch_command_values,
    switch_icon,
)

_LOGGER = logging.getLogger(__name__)


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
    on_value: Any
    off_value: Any
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
    if not is_writable_auxiliary_property(prop, component):
        _log_property_control_skip(
            "number",
            instance,
            component,
            prop,
            auxiliary_property_skip_reason(prop, component),
        )
        return None
    value_range = control_value_range(prop)
    if value_range is None or control_value_list(prop):
        _log_property_control_skip(
            "number",
            instance,
            component,
            prop,
            "missing_numeric_range_or_is_enum",
        )
        return None

    numeric_range = NumericRange(
        min=value_range.min,
        max=value_range.max,
        step=value_range.step,
    )
    return HANumberControlProjection(
        component_id=f"{component.component_id}_{prop.prop_id}_number",
        prop_id=prop.prop_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}_{prop.prop_id}_number",
        name=control_name(component, prop, device_payload=device_payload),
        available=control_available(device_payload, instance, component),
        value=to_float(
            component_property_value(
                _params(device_payload),
                instance,
                component,
                prop.prop_id,
            )
        ),
        native_range=numeric_range,
        unit=control_unit(prop),
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
    if not is_writable_auxiliary_property(prop, component):
        _log_property_control_skip(
            "select",
            instance,
            component,
            prop,
            auxiliary_property_skip_reason(prop, component),
        )
        return None
    value_list = control_value_list(prop)
    if not value_list:
        _log_property_control_skip(
            "select",
            instance,
            component,
            prop,
            "missing_value_list",
        )
        return None
    options = tuple(select_options(value_list, HASelectOption))
    if not options:
        _log_property_control_skip(
            "select",
            instance,
            component,
            prop,
            "empty_select_options",
        )
        return None

    return HASelectControlProjection(
        component_id=f"{component.component_id}_{prop.prop_id}_select",
        prop_id=prop.prop_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}_{prop.prop_id}_select",
        name=control_name(component, prop, device_payload=device_payload),
        available=control_available(device_payload, instance, component),
        value=component_property_value(
            _params(device_payload),
            instance,
            component,
            prop.prop_id,
        ),
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
    if not is_writable_auxiliary_bool_property(prop, component):
        _log_property_control_skip(
            "switch",
            instance,
            component,
            prop,
            auxiliary_bool_property_skip_reason(prop, component),
        )
        return None

    on_value, off_value = switch_command_values(prop)
    return HASwitchControlProjection(
        component_id=f"{component.component_id}_{prop.prop_id}_switch",
        prop_id=prop.prop_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}_{prop.prop_id}_switch",
        name=control_name(component, prop, device_payload=device_payload),
        available=control_available(device_payload, instance, component),
        is_on=to_bool(
            component_property_value(
                _params(device_payload),
                instance,
                component,
                prop.prop_id,
            ),
            default=to_bool(prop.default, default=False),
        ),
        on_value=on_value,
        off_value=off_value,
        control_key=control_key(instance, component.component_id, prop.prop_id),
        device_info=project_payload_device_info(device_payload, instance),
        icon=switch_icon(prop),
        entity_category=entity_category_for_property(prop.prop_id),
    )


def _log_property_control_skip(
    platform: str,
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    prop: PropertyModel,
    reason: str | None,
) -> None:
    """Log why a schema property did not become a helper entity."""
    _LOGGER.debug(
        "Skipping %s property control projection: device_id=%s component_id=%s "
        "category=%s prop_id=%s access=%s type=%s reason=%s",
        platform,
        instance.device_id,
        component.component_id,
        component.category,
        prop.prop_id,
        prop.access,
        prop.property_type or prop.kind or prop.format,
        reason or "unknown",
    )


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """提取 raw params，供组件 scoped key 读取当前值."""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


__all__ = [
    "HANumberControlProjection",
    "HASelectControlProjection",
    "HASelectOption",
    "HASwitchControlProjection",
    "project_number_controls",
    "project_select_controls",
    "project_switch_controls",
]
