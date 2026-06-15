"""Canonical product-model helpers for documented Yeelight catalog data."""

from __future__ import annotations

from typing import Any

from ..canonical.models import (
    BridgeModel,
    ComponentModel,
    EventModel,
    HAProductModel,
    ProductModel,
    PropertyModel,
    ValueItemModel,
    ValueRangeModel,
)
from .models import IoTComponentSpec, IoTProductSpec


def build_product_model(
    spec: IoTProductSpec,
    catalog_components: tuple[IoTComponentSpec, ...],
    protocols: tuple[str, ...],
    property_builder: Any,
) -> HAProductModel | None:
    """Build a conservative canonical model from documented product data."""
    duplicate_counts: dict[str, int] = {}
    for component in catalog_components:
        base = _catalog_component_id_base_key(component)
        duplicate_counts[base] = duplicate_counts.get(base, 0) + 1

    occurrence_counts: dict[str, int] = {}
    components: list[ComponentModel] = []
    for component in catalog_components:
        base = _catalog_component_id_base_key(component)
        occurrence_counts[base] = occurrence_counts.get(base, 0) + 1
        component_index = (
            occurrence_counts[base]
            if duplicate_counts[base] > 1
            else None
        )
        components.append(
            _component_model(component, property_builder, index=component_index)
        )
    if not components:
        return None

    categories = _dedupe(component.category for component in components if component.category)
    return HAProductModel(
        schema_version="catalog-v1",
        product=ProductModel(
            model_id=f"YL-{spec.pid}",
            manufacturer="Yeelight",
            model=spec.name,
            description="Documented Yeelight IoT product composition",
            category=categories[0] if len(categories) == 1 else None,
            categories=categories,
            bridge=BridgeModel(protocols=list(protocols)),
        ),
        components=components,
        device_actions=[],
        notes=[
            "This product model is derived from Yeelight IoT product composition.",
            "Runtime property values must still come from live device payloads.",
        ],
    )


def registry_property_model(prop_id: str, registry: Any) -> PropertyModel | None:
    """用 registry 属性定义构建 canonical property。"""
    spec = registry.property_spec(prop_id)
    if spec is None:
        return None
    return PropertyModel(
        prop_id=spec.prop,
        name=spec.display_name,
        desc=spec.description,
        semantic=spec.full_name,
        kind="control" if spec.writable else "state",
        property_type="apply" if spec.category == "application" else "config",
        format=spec.data_type,
        unit=spec.unit,
        access="read_write" if spec.writable else "read_only",
        value_range=(
            ValueRangeModel(
                min=_range_value(spec.value_range[0]),
                max=_range_value(spec.value_range[1]),
                step=_range_value(spec.value_range[2]),
            )
            if spec.value_range is not None
            else None
        ),
        value_list=[
            ValueItemModel(code=str(code), desc=str(label))
            for code, label in spec.value_list.items()
        ],
    )


def _component_model(
    component: IoTComponentSpec,
    property_builder: Any,
    *,
    index: int | None = None,
) -> ComponentModel:
    properties = [
        prop_model
        for prop_id in component.properties
        if (prop_model := property_builder(prop_id, component.category or "")) is not None
    ]
    return ComponentModel(
        component_id=_catalog_component_id(component, index=index),
        cid=component.component_id,
        index=index,
        name=component.name,
        desc=component.name,
        component_type=component.component_type,
        category=component.category,
        capabilities=_component_capabilities(component, properties),
        properties=properties,
        events=[
            EventModel(name=event_type, semantic=event_type, params=[])
            for event_type in component.events
        ],
        actions=[],
    )


def _catalog_component_id(component: IoTComponentSpec, *, index: int | None) -> str:
    base = _catalog_component_base(component)
    component_id = str(base).replace(" ", "_")
    return f"{component_id}_{index}" if index is not None else component_id


def _catalog_component_base(component: IoTComponentSpec) -> str:
    """Return an IoT-shaped component id instead of a HA helper platform id."""
    if component.component_type == "global":
        return component.alias
    if component.category in {
        "contact_sensor",
        "curtain",
        "gateway",
        "human_sensor",
        "knob_switch",
        "light_sensor",
        "other",
        "scene_panel",
    }:
        return component.category
    return component.platform_hint or component.category or component.alias


def _catalog_component_id_base_key(component: IoTComponentSpec) -> str:
    """Return the generated component-id base used for duplicate indexing."""
    return str(_catalog_component_base(component)).replace(" ", "_")


def _component_capabilities(
    component: IoTComponentSpec,
    properties: list[PropertyModel],
) -> list[str]:
    prop_ids = {prop.prop_id for prop in properties}
    if component.category == "light":
        capabilities = ["onoff"]
        if "l" in prop_ids:
            capabilities.append("brightness")
        if "ct" in prop_ids:
            capabilities.append("color_temp")
        if "c" in prop_ids:
            capabilities.append("rgb")
        return capabilities
    if component.category == "relay_switch":
        return ["onoff"]
    if component.category in {"curtain", "temp_control"}:
        return sorted(prop_ids)
    if component.category in {"contact_sensor", "human_sensor", "light_sensor", "other"}:
        return sorted(prop_ids)
    return []


def _range_value(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _dedupe(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


__all__ = ["build_product_model", "registry_property_model"]
