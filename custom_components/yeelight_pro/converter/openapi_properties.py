"""OpenAPI property metadata conversion helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..canonical.models import PropertyModel, ValueItemModel, ValueRangeModel
from ..capabilities.models import IoTPropertySpec
from ..capabilities.registry import property_spec
from ..utils import normalize_scale, normalize_unit, normalize_zoom, to_int

PropertyBuilder = Callable[[str, str], PropertyModel | None]
StringNormalizer = Callable[[Any], str | None]

TEMPLATE_FALLBACK_KEYS = (
    "light",
    "relay_switch",
    "switch",
    "fan",
    "fresh_air",
    "curtain",
    "contact_sensor",
    "human_sensor",
    "light_sensor",
    "sensor",
    "other",
    "temp_control",
    "climate",
)


def openapi_property_model(
    prop_id: str,
    prop: Mapping[str, Any],
    *,
    category: str | None,
    build_property: PropertyBuilder,
    string_value: StringNormalizer,
) -> PropertyModel | None:
    """Build a canonical property model from OpenAPI metadata or CSV registry."""
    template = build_property(prop_id, category or "") or template_property(
        prop_id,
        build_property,
    )
    spec = property_spec(prop_id)

    desc = string_value(prop.get("desc")) or string_value(prop.get("name"))
    prop_format = string_value(prop.get("format", prop.get("fomat")))
    unit = normalize_unit(prop.get("unit"))
    access = openapi_property_access(prop, string_value)
    value_range = openapi_value_range(prop.get("valueRange"))
    value_list = openapi_value_list(prop.get("valueList"), string_value)

    if not any((desc, prop_format, unit, access, value_range, value_list)):
        if template is not None:
            return template
        if spec is None:
            return None

    return PropertyModel(
        prop_id=prop_id,
        name=desc
        or (template.name if template is not None else None)
        or (spec.display_name if spec is not None else None),
        desc=desc or (spec.description if spec is not None else None),
        semantic=template.semantic if template is not None else (
            spec.full_name if spec is not None else None
        ),
        kind=_property_kind(access, spec)
        or (template.kind if template is not None else None),
        property_type=(
            template.property_type
            if template is not None
            else _property_type_from_spec(spec)
        ),
        format=prop_format
        or (template.format if template is not None else None)
        or _format_from_spec(spec),
        unit=unit or (template.unit if template is not None else None) or _unit(spec),
        zoom=normalize_zoom(prop.get("zoom")),
        scale=normalize_scale(prop.get("scale")),
        access=access
        or (template.access if template is not None else None)
        or _access_from_spec(spec),
        value_range=value_range
        or (template.value_range if template is not None else None)
        or _value_range_from_spec(spec),
        value_list=value_list
        or (template.value_list if template is not None else [])
        or _value_list_from_spec(spec),
    )


def template_property(
    prop_id: str,
    build_property: PropertyBuilder,
) -> PropertyModel | None:
    """Find a runtime template property without relying on a device category."""
    for template_key in TEMPLATE_FALLBACK_KEYS:
        if template := build_property(prop_id, template_key):
            return template
    return None


def openapi_runtime_properties(
    category: str | None,
    payload: Mapping[str, Any] | None,
    *,
    build_property: PropertyBuilder,
    string_value: StringNormalizer,
) -> list[PropertyModel]:
    """Return canonical property models from top-level OpenAPI properties."""
    if not isinstance(payload, Mapping):
        return []

    properties: list[PropertyModel] = []
    for prop in openapi_property_rows(payload.get("properties")):
        prop_id = string_value(prop.get("propId", prop.get("propName")))
        if not prop_id:
            continue
        property_model = openapi_property_model(
            prop_id,
            prop,
            category=category,
            build_property=build_property,
            string_value=string_value,
        )
        if property_model is not None:
            properties.append(property_model)
    return properties


def openapi_property_access(
    prop: Mapping[str, Any],
    string_value: StringNormalizer,
) -> str | None:
    """Infer read/write semantics from OpenAPI operators or access fields."""
    operators = {
        str(item).strip().lower()
        for item in prop.get("operators") or []
        if str(item).strip()
    }
    if operators & {"set", "toggle", "adjust"}:
        return "read_write"
    access = prop.get("access")
    numeric_access = to_int(access)
    if numeric_access is not None:
        return "read_write" if numeric_access & 2 else "read_only"
    access_text = string_value(access)
    if access_text and _access_allows_write(access_text):
        return "read_write"
    if access_text and _access_is_read_only(access_text):
        return "read_only"
    return access_text


def openapi_value_range(value: Any) -> ValueRangeModel | None:
    """Convert an OpenAPI valueRange object to canonical metadata."""
    if not isinstance(value, Mapping):
        return None
    return ValueRangeModel(
        min=to_int(value.get("min")),
        max=to_int(value.get("max")),
        step=to_int(value.get("step")),
    )


def openapi_value_list(
    value: Any,
    string_value: StringNormalizer,
) -> list[ValueItemModel]:
    """Convert an OpenAPI valueList array to canonical metadata."""
    items: list[ValueItemModel] = []
    for item in value or []:
        if not isinstance(item, Mapping):
            continue
        code = string_value(item.get("code"))
        if not code:
            continue
        items.append(ValueItemModel(code=code, desc=string_value(item.get("desc"))))
    return items


def _property_kind(
    access: str | None,
    spec: IoTPropertySpec | None,
) -> str | None:
    if spec is not None and spec.category == "config":
        return "config"
    if access == "read_write":
        return "control"
    if access == "read_only":
        return "state"
    return None


def _property_type_from_spec(spec: IoTPropertySpec | None) -> str:
    if spec is None:
        return "apply"
    return "config" if spec.category == "config" else "apply"


def _format_from_spec(spec: IoTPropertySpec | None) -> str | None:
    return spec.data_type if spec is not None and spec.data_type else None


def _unit(spec: IoTPropertySpec | None) -> str | None:
    return spec.unit if spec is not None else None


def _access_from_spec(spec: IoTPropertySpec | None) -> str | None:
    if spec is None:
        return None
    if spec.readable and spec.writable:
        return "read_write"
    if spec.readable:
        return "read_only"
    if spec.writable:
        return "write_only"
    return spec.access or None


def _value_range_from_spec(spec: IoTPropertySpec | None) -> ValueRangeModel | None:
    if spec is None or spec.value_range is None:
        return None
    minimum, maximum, step = spec.value_range
    return ValueRangeModel(
        min=to_int(minimum),
        max=to_int(maximum),
        step=to_int(step),
    )


def _value_list_from_spec(spec: IoTPropertySpec | None) -> list[ValueItemModel]:
    if spec is None or not spec.value_list:
        return []
    return [
        ValueItemModel(code=str(code), desc=str(label))
        for code, label in spec.value_list.items()
    ]


def _access_allows_write(value: str) -> bool:
    lowered = value.lower()
    return "write" in lowered or "写" in value


def _access_is_read_only(value: str) -> bool:
    lowered = value.lower().replace(" ", "").replace("-", "_")
    return lowered in {"read", "read_only", "readonly", "ro", "r"} or value == "读"


__all__ = [
    "openapi_property_access",
    "openapi_property_model",
    "openapi_property_rows",
    "openapi_runtime_properties",
    "openapi_value_list",
    "openapi_value_range",
    "template_property",
]


def openapi_property_rows(value: Any) -> list[Mapping[str, Any]]:
    """Return property mappings from OpenAPI response variants."""
    return [item for item in value or [] if isinstance(item, Mapping)]
