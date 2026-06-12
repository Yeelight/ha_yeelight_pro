"""Shared helpers for writable property control projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..canonical.models import (
    ComponentInstanceModel,
    HADeviceInstanceModel,
    PropertyModel,
    ValueItemModel,
    ValueRangeModel,
)
from ..capabilities.registry import (
    format_component_property_key,
    property_spec,
)
from ..device_display import channel_name_label
from ..entity_category import entity_category_for_property
from ..utils import to_str
from .common import (
    component_index,
    humanize_component_id,
    load_product_model,
    payload_available,
    product_component,
    schema_backed_component_available,
)
from .switch_helpers import _component_state_key_map
from .platform_evidence import component_platform

MAIN_ENTITY_PROPS = frozenset({
    "p",
    "sp",
    "l",
    "ct",
    "c",
    "cp",
    "tp",
    "rs",
    "acp",
    "actt",
    "acct",
    "rfhp",
    "rfhct",
    "rfhtt",
    "tgt",
    "vmcp",
    "vmcf",
    "m",
    "lock",
    "locked",
    "lck",
})
MAIN_ENTITY_PROPS_BY_PLATFORM = {
    "climate": frozenset({
        "acp",
        "actt",
        "acct",
        "p",
        "rfhp",
        "rfhct",
        "rfhtt",
        "tgt",
    }),
    "cover": frozenset({"cp", "rs", "tp"}),
    "fan": frozenset({"vmcp", "vmcf"}),
    "light": frozenset({"c", "ct", "l", "m", "p"}),
    "switch": frozenset({"p", "sp"}),
}
BOOL_FORMATS = frozenset({"bool", "boolean"})
AUXILIARY_BOOL_CONFIG_PROPS = frozenset({
    "acrc",
    "blp",
    "keys_visible",
    "lc",
    "li",
    "ntOn",
    "temp_hidden",
    "time_hidden",
    "weather_hidden",
})


def schema_properties(
    device_payload: Mapping[str, Any],
    component: ComponentInstanceModel,
) -> list[PropertyModel]:
    """Return schema properties for a component."""
    product_model = load_product_model(device_payload)
    product = product_component(product_model, component.component_id)
    return list(product.properties) if product is not None else []


def is_writable_auxiliary_property(
    prop: PropertyModel,
    component: ComponentInstanceModel | None = None,
) -> bool:
    """Return true for writable range/enum properties owned by helper entities."""
    return auxiliary_property_skip_reason(prop, component) is None


def auxiliary_property_skip_reason(
    prop: PropertyModel,
    component: ComponentInstanceModel | None = None,
) -> str | None:
    """Return why a range/enum property cannot become a helper entity."""
    spec = property_spec(prop.prop_id)
    if spec is None or not spec.writable:
        return "undocumented_or_registry_read_only_property"
    if _is_main_entity_property(prop.prop_id, component):
        return "owned_by_main_entity"
    if looks_bool(prop):
        return "boolean_property"
    if not _access_allows_write(prop.access):
        return "schema_read_only"
    return None


def is_writable_auxiliary_bool_property(
    prop: PropertyModel,
    component: ComponentInstanceModel | None = None,
) -> bool:
    """Return true for documented writable bool helper properties."""
    return auxiliary_bool_property_skip_reason(prop, component) is None


def auxiliary_bool_property_skip_reason(
    prop: PropertyModel,
    component: ComponentInstanceModel | None = None,
) -> str | None:
    """Return why a bool property cannot become a helper switch entity."""
    spec = property_spec(prop.prop_id)
    if spec is None or not spec.writable:
        return "undocumented_or_registry_read_only_property"
    if _is_main_entity_property(prop.prop_id, component):
        return "owned_by_main_entity"
    if not looks_bool(prop):
        return "not_boolean_property"
    if not _access_allows_write(prop.access):
        return "schema_read_only"
    return None


def control_available(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
) -> bool:
    """Keep schema-backed controls available when current read state is sparse."""
    product_model = load_product_model(device_payload)
    return schema_backed_component_available(
        payload_available(device_payload, instance),
        component,
        schema_component=product_component(product_model, component.component_id),
    )


def looks_bool(prop: PropertyModel) -> bool:
    """Return whether a property has boolean semantics."""
    if prop.prop_id in AUXILIARY_BOOL_CONFIG_PROPS:
        return True
    values = {prop.kind, prop.property_type, prop.format}
    if any((item or "").lower() in BOOL_FORMATS for item in values):
        return True
    spec = property_spec(prop.prop_id)
    return bool(spec is not None and spec.data_type.lower() in BOOL_FORMATS)


def _is_main_entity_property(
    prop_id: str,
    component: ComponentInstanceModel | None,
) -> bool:
    """Return whether a property is already owned by the component's main entity."""
    if component is None:
        return prop_id in MAIN_ENTITY_PROPS

    platform = _component_platform(component)
    if platform in MAIN_ENTITY_PROPS_BY_PLATFORM:
        return prop_id in MAIN_ENTITY_PROPS_BY_PLATFORM[platform]
    if platform is None and _looks_like_relay_switch_component(component):
        return prop_id in MAIN_ENTITY_PROPS_BY_PLATFORM["switch"]
    return prop_id in MAIN_ENTITY_PROPS


def _component_platform(component: ComponentInstanceModel) -> str | None:
    """Return documented HA platform for a component without using labels."""
    return component_platform(component)


def _looks_like_relay_switch_component(component: ComponentInstanceModel) -> bool:
    """Return true for canonical relay-switch channels with power control."""
    category = (component.category or "").lower()
    return category in {"relay_switch", "switch"}


def control_value_range(prop: PropertyModel) -> ValueRangeModel | None:
    """Return schema or registry-backed numeric range metadata."""
    if prop.value_range is not None:
        return prop.value_range
    spec = property_spec(prop.prop_id)
    if spec is None or spec.value_range is None:
        return None
    minimum, maximum, step = spec.value_range
    return ValueRangeModel(
        min=_range_value(minimum),
        max=_range_value(maximum),
        step=_range_value(step),
    )


def control_value_list(prop: PropertyModel) -> list[ValueItemModel]:
    """Return schema or registry-backed enum metadata."""
    if prop.value_list:
        return prop.value_list
    spec = property_spec(prop.prop_id)
    if spec is None or not spec.value_list:
        return []
    return [
        ValueItemModel(code=str(code), desc=to_str(label) or str(code))
        for code, label in spec.value_list.items()
    ]


def control_unit(prop: PropertyModel) -> str | None:
    """Return schema or registry-backed unit metadata."""
    if prop.unit:
        return prop.unit
    spec = property_spec(prop.prop_id)
    return spec.unit if spec is not None else None


def switch_command_values(prop: PropertyModel) -> tuple[Any, Any]:
    """Return raw on/off values matching the Yeelight property type."""
    spec = property_spec(prop.prop_id)
    data_type = prop.property_type or (spec.data_type if spec is not None else "") or ""
    if data_type.lower() in {"int", "integer", "uint8", "uint16", "uint32"}:
        return 1, 0
    return True, False


def _range_value(value: Any) -> int | None:
    """Return the integer range value supported by canonical ValueRangeModel."""
    if value is None:
        return None
    return int(value)


def _access_allows_write(value: str | None) -> bool:
    """Return true for normalized or documented writable access text."""
    if value is None:
        return False
    access = value.lower()
    return "write" in access or "写" in value


def control_key(
    instance: HADeviceInstanceModel,
    component_id: str,
    prop_id: str,
) -> str:
    """Return the runtime control key for a component property."""
    mapped = _component_state_key_map(instance).get(component_id, {}).get(prop_id)
    if mapped:
        return mapped
    return format_component_property_key(component_index(component_id), prop_id)


def control_name(
    component: ComponentInstanceModel,
    prop: PropertyModel,
    *,
    device_payload: Mapping[str, Any] | None = None,
) -> str | None:
    """Return a user-facing helper entity name."""
    prop_name = property_label(prop)
    channel_name = channel_name_label(
        index=component_index(component.component_id),
        component=component,
        device_payload=device_payload,
    )
    component_name = channel_name or humanize_component_id(component.component_id)
    if _same_label(component_name, device_payload):
        component_name = None
    if component_name and prop_name:
        return f"{component_name} {prop_name}"
    return prop_name or component_name


def property_label(prop: PropertyModel) -> str | None:
    """Return a user-facing property label."""
    spec = property_spec(prop.prop_id)
    for value in (prop.name, prop.desc):
        if text := to_str(value):
            if spec is not None and text == spec.full_name and spec.description:
                return spec.display_name
            return text
    if spec is not None:
        return spec.display_name
    return prop.prop_id


def _same_label(value: str | None, payload: Mapping[str, Any] | None) -> bool:
    """Return whether component label duplicates the device label."""
    if value is None or payload is None:
        return False
    names = (
        payload.get("name"),
        payload.get("deviceName"),
        payload.get("device_name"),
        payload.get("n"),
    )
    normalized = _normalize_label(value)
    return any(normalized == _normalize_label(item) for item in names)


def _normalize_label(value: Any) -> str:
    text = to_str(value)
    return "".join((text or "").split())


def select_options(items: list[ValueItemModel], option_cls: Any) -> list[Any]:
    """Return unique select options using the provided projection option class."""
    options: list[Any] = []
    seen_labels: set[str] = set()
    for item in items:
        if not item.code:
            continue
        label = to_str(item.desc) or item.code
        if label in seen_labels:
            label = f"{label} ({item.code})"
        seen_labels.add(label)
        options.append(option_cls(value=item.code, label=label))
    return options


def number_icon(prop: PropertyModel) -> str | None:
    """Return an icon for numeric helper controls."""
    if prop.unit == "%":
        return "mdi:tune-variant"
    return "mdi:numeric"


def select_icon(prop: PropertyModel) -> str | None:
    """Return an icon for enum helper controls."""
    if prop.prop_id in {"rd", "dir"}:
        return "mdi:swap-horizontal"
    return "mdi:form-dropdown"


def switch_icon(prop: PropertyModel) -> str | None:
    """Return an icon for bool helper controls."""
    if prop.prop_id == "acrc":
        return "mdi:remote"
    return "mdi:toggle-switch"


__all__ = [
    "control_available",
    "control_key",
    "control_name",
    "control_unit",
    "control_value_list",
    "control_value_range",
    "entity_category_for_property",
    "auxiliary_bool_property_skip_reason",
    "auxiliary_property_skip_reason",
    "is_writable_auxiliary_bool_property",
    "is_writable_auxiliary_property",
    "number_icon",
    "schema_properties",
    "select_icon",
    "select_options",
    "switch_command_values",
    "switch_icon",
]
