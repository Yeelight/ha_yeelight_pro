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
    "dir",
    "lock",
    "locked",
    "lck",
})
BOOL_FORMATS = frozenset({"bool", "boolean"})
AUXILIARY_BOOL_CONFIG_PROPS = frozenset({
    "acrc",
    "blp",
    "keys_visible",
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
    if _is_main_entity_property(prop.prop_id, component):
        return False
    if looks_bool(prop):
        return False
    if not _access_allows_write(prop.access):
        return False
    spec = property_spec(prop.prop_id)
    if spec is not None and not spec.writable:
        return False
    return True


def is_writable_auxiliary_bool_property(
    prop: PropertyModel,
    component: ComponentInstanceModel | None = None,
) -> bool:
    """Return true for documented writable bool helper properties."""
    if _is_main_entity_property(prop.prop_id, component):
        return False
    if not looks_bool(prop):
        return False
    if not _access_allows_write(prop.access):
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

    category = (component.category or "").lower()
    if any(token in category for token in ("relay_switch", "switch", "开关")):
        return prop_id in {"p", "sp", "on"}
    if any(token in category for token in ("light", "灯", "彩光", "色温")):
        return prop_id in {"p", "on", "l", "ct", "c", "m"}
    if any(token in category for token in ("curtain", "blind", "窗帘")):
        return prop_id in {"cp", "tp", "rs"}
    if any(token in category for token in ("fresh air", "fan", "新风")):
        return prop_id in {"vmcp", "vmcf"}
    if any(token in category for token in ("temp_control", "climate", "空调", "地暖")):
        return prop_id in {"acp", "actt", "acct", "rfhp", "rfhct", "rfhtt", "tgt"}
    return prop_id in MAIN_ENTITY_PROPS


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
    "control_unit",
    "control_value_list",
    "control_value_range",
    "entity_category_for_property",
    "is_writable_auxiliary_bool_property",
    "is_writable_auxiliary_property",
    "number_icon",
    "schema_properties",
    "select_icon",
    "select_options",
    "switch_command_values",
    "switch_icon",
]
