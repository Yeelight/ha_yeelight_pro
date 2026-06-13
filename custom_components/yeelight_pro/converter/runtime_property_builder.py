"""Runtime property model builder backed by Yeelight IoT registry."""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import PropertyModel, ValueItemModel, ValueRangeModel
from ..capabilities.registry import property_spec
from .openapi_properties import openapi_runtime_properties
from .runtime_templates import RUNTIME_PROPERTY_TEMPLATES


def infer_runtime_properties(
    template_key: str | None,
    params: Mapping[str, Any],
    *,
    payload: Mapping[str, Any] | None = None,
    string_value: Any,
) -> list[PropertyModel]:
    """Infer runtime properties from OpenAPI rows and documented params."""
    templates = RUNTIME_PROPERTY_TEMPLATES.get(template_key or "")
    if not templates:
        return []

    source_props: tuple[str, ...]
    if params:
        source_props = _ordered_runtime_property_ids(params)
    else:
        source_props = ()

    properties = {
        prop.prop_id: prop
        for prop in openapi_runtime_properties(
            template_key,
            payload,
            build_property=build_runtime_property_model,
            string_value=string_value,
        )
    }
    for prop_id in source_props:
        property_model = build_runtime_property_model(prop_id, template_key or "")
        if property_model is not None:
            properties.setdefault(prop_id, property_model)
    return list(properties.values())


def _ordered_runtime_property_ids(params: Mapping[str, Any]) -> tuple[str, ...]:
    """Return property ids from params while preserving payload order."""
    ordered: list[str] = []
    for raw_prop in params:
        prop = str(raw_prop).split("-", 1)[-1]
        if prop not in ordered:
            ordered.append(prop)
    return tuple(ordered)


def build_runtime_property_model(
    prop_id: str,
    device_type: str,
) -> PropertyModel | None:
    """Build a runtime property model from templates or the IoT registry."""
    template = RUNTIME_PROPERTY_TEMPLATES.get(device_type, {}).get(prop_id)
    if template is None:
        return _registry_runtime_property_model(prop_id)

    value_range = template.get("value_range")
    spec = property_spec(prop_id)
    return PropertyModel(
        prop_id=prop_id,
        name=template.get("name") or (spec.display_name if spec is not None else None),
        kind=template.get("kind"),
        property_type=template.get("property_type"),
        format=template.get("format"),
        unit=template.get("unit"),
        access=template.get("access"),
        value_range=(
            ValueRangeModel(
                min=value_range[0],
                max=value_range[1],
                step=value_range[2],
            )
            if value_range is not None
            else None
        ),
    )


def _registry_runtime_property_model(prop_id: str) -> PropertyModel | None:
    """Build a runtime property from the embedded Yeelight IoT registry."""
    spec = property_spec(prop_id)
    if spec is None:
        return None
    return PropertyModel(
        prop_id=spec.prop,
        name=spec.display_name,
        desc=spec.description,
        semantic=spec.full_name,
        kind="control" if spec.writable else "state",
        property_type="config" if spec.category == "config" else "apply",
        format=spec.data_type,
        unit=spec.unit,
        access=_registry_access(spec),
        value_range=_registry_value_range(spec.value_range),
        value_list=[
            ValueItemModel(code=str(code), desc=str(label))
            for code, label in spec.value_list.items()
        ],
    )


def _registry_access(spec: Any) -> str:
    """Return canonical access text for a registry property."""
    if spec.readable and spec.writable:
        return "read_write"
    if spec.readable:
        return "read_only"
    if spec.writable:
        return "write_only"
    return str(spec.access or "")


def _registry_value_range(value_range: Any) -> ValueRangeModel | None:
    """Convert registry value range tuples to canonical models."""
    if value_range is None:
        return None
    minimum, maximum, step = value_range
    return ValueRangeModel(
        min=_int_value(minimum),
        max=_int_value(maximum),
        step=_int_value(step),
    )


def _int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "build_runtime_property_model",
    "infer_runtime_properties",
]
