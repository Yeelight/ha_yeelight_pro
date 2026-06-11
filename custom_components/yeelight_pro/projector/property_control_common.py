"""Shared helpers for writable property control projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..canonical.models import (
    ComponentInstanceModel,
    HADeviceInstanceModel,
    PropertyModel,
    ValueItemModel,
)
from ..capabilities.registry import format_component_property_key, property_spec
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

MAIN_ENTITY_PROPS = frozenset({
    "p",
    "sp",
    "on",
    "l",
    "ct",
    "c",
    "c_waf",
    "c_xy",
    "cp",
    "tp",
    "rs",
    "acp",
    "aco",
    "acm",
    "actt",
    "acct",
    "acf",
    "rfhp",
    "rfhct",
    "rfhtt",
    "tgt",
    "fa",
    "he",
    "vmcp",
    "vmcf",
    "lv",
    "m",
    "dir",
    "lock",
    "locked",
    "lck",
})
BOOL_FORMATS = frozenset({"bool", "boolean"})
AUXILIARY_BOOL_CONFIG_PROPS = frozenset({
    "acrc",
    "keys_visible",
    "nightMode",
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


def is_writable_auxiliary_property(prop: PropertyModel) -> bool:
    """Return true for writable range/enum properties owned by helper entities."""
    if prop.prop_id in MAIN_ENTITY_PROPS:
        return False
    if looks_bool(prop):
        return False
    access = (prop.access or "").lower()
    if "write" not in access:
        return False
    spec = property_spec(prop.prop_id)
    if spec is not None and not spec.writable:
        return False
    return True


def is_writable_auxiliary_bool_property(prop: PropertyModel) -> bool:
    """Return true for documented writable bool helper properties."""
    if prop.prop_id in MAIN_ENTITY_PROPS:
        return False
    if not looks_bool(prop):
        return False
    access = (prop.access or "").lower()
    if "write" not in access:
        return False
    spec = property_spec(prop.prop_id)
    if spec is not None and not spec.writable:
        return False
    return True


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
    values = {prop.kind, prop.property_type, prop.format}
    return any((item or "").lower() in BOOL_FORMATS for item in values)


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
    if component_name and prop_name:
        return f"{component_name} {prop_name}"
    return prop_name or component_name


def property_label(prop: PropertyModel) -> str | None:
    """Return a user-facing property label."""
    for value in (prop.name, prop.desc):
        if text := to_str(value):
            return text
    spec = property_spec(prop.prop_id)
    if spec is not None:
        return spec.full_name
    return prop.prop_id


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
    "entity_category_for_property",
    "is_writable_auxiliary_bool_property",
    "is_writable_auxiliary_property",
    "number_icon",
    "schema_properties",
    "select_icon",
    "select_options",
    "switch_icon",
]
