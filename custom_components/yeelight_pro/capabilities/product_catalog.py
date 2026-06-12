"""Yeelight IoT 产品构成目录查询与模型构建."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from functools import lru_cache
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
from ..utils import to_int
from .models import IoTComponentSpec, IoTProductSpec
from .product_catalog_data import IOT_PRODUCT_SPECS

PROJECTABLE_GLOBAL_COMPONENTS = frozenset({
    "basic",
    "battery",
    "backlight indicator",
    "power meter",
    "dali energy",
    "hvac gateway",
})


@lru_cache(maxsize=1)
def product_catalog() -> dict[int, IoTProductSpec]:
    """返回 pid -> 产品构成定义."""
    return {item.pid: item for item in IOT_PRODUCT_SPECS}


def product_spec(pid: Any) -> IoTProductSpec | None:
    """按 pid 查询产品构成定义."""
    normalized = normalize_product_pid(pid)
    if normalized is None:
        return None
    return product_catalog().get(normalized)


def normalize_product_pid(pid: Any) -> int | None:
    """归一化易来产品 pid，兼容 CSV/接口中的科学计数法文本."""
    direct = to_int(pid)
    if direct is not None:
        return direct
    if pid is None:
        return None
    text = str(pid).strip()
    if not text:
        return None
    try:
        decimal = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not decimal.is_finite() or decimal != decimal.to_integral_value():
        return None
    return int(decimal)


def product_components(
    pid: Any,
    component_map: dict[str, IoTComponentSpec],
) -> tuple[IoTComponentSpec, ...]:
    """返回产品声明的普通组件定义，按产品构成顺序展开."""
    spec = product_spec(pid)
    if spec is None:
        return ()
    components: list[IoTComponentSpec] = []
    for name in _expanded_component_names(spec):
        component = component_map.get(_component_key(name))
        if component is not None:
            components.append(component)
    return tuple(components)


def product_projectable_global_components(
    pid: Any,
    component_map: dict[str, IoTComponentSpec],
) -> tuple[IoTComponentSpec, ...]:
    """Return documented global components with safe HA projection semantics."""
    spec = product_spec(pid)
    if spec is None:
        return ()
    components: list[IoTComponentSpec] = []
    for name in spec.global_components:
        component = component_map.get(_component_key(name))
        if component is not None and _projectable_global_component(component):
            components.append(component)
    return tuple(components)


def is_projectable_global_component(component: Any) -> bool:
    """Return true for documented global components safe to expose in HA."""
    return any(
        _component_key(value) in PROJECTABLE_GLOBAL_COMPONENTS
        for value in (
            getattr(component, "alias", None),
            getattr(component, "component_id", None),
            getattr(component, "name", None),
        )
    )


def product_category_candidates(
    pid: Any,
    component_map: dict[str, IoTComponentSpec],
) -> tuple[str, ...]:
    """返回产品普通组件声明出的 IoT 品类候选."""
    seen: set[str] = set()
    categories: list[str] = []
    for component in product_components(pid, component_map):
        if component.category is None or component.category in seen:
            continue
        seen.add(component.category)
        categories.append(component.category)
    return tuple(categories)


def product_protocols(pid: Any) -> tuple[str, ...]:
    """返回产品接入协议与桥协议文本."""
    spec = product_spec(pid)
    if spec is None:
        return ()
    protocols: list[str] = []
    if spec.protocol:
        protocols.append(spec.protocol)
    protocols.extend(spec.bridge_protocols)
    return tuple(protocols)


def product_model_from_catalog(
    pid: Any,
    component_map: dict[str, IoTComponentSpec],
    property_builder: Any,
) -> HAProductModel | None:
    """从产品构成目录构建保守 canonical 产品模型."""
    spec = product_spec(pid)
    if spec is None:
        return None
    global_components = product_projectable_global_components(spec.pid, component_map)
    catalog_components = (*global_components, *product_components(spec.pid, component_map))
    duplicate_counts: dict[int, int] = {}
    for component in catalog_components:
        duplicate_counts[component.component_id] = duplicate_counts.get(component.component_id, 0) + 1

    occurrence_counts: dict[int, int] = {}
    components: list[ComponentModel] = []
    for component in catalog_components:
        occurrence_counts[component.component_id] = occurrence_counts.get(component.component_id, 0) + 1
        component_index = (
            occurrence_counts[component.component_id]
            if duplicate_counts[component.component_id] > 1
            else None
        )
        components.append(_component_model(component, property_builder, index=component_index))
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
            bridge=BridgeModel(protocols=list(product_protocols(spec.pid))),
        ),
        components=components,
        device_actions=[],
        notes=[
            "This product model is derived from Yeelight IoT product composition.",
            "Runtime property values must still come from live device payloads.",
        ],
    )


def product_hydration_properties(
    pid: Any,
    component_map: dict[str, IoTComponentSpec],
) -> tuple[str, ...]:
    """返回产品组件声明出的属性读取集合."""
    props: list[str] = []
    seen: set[str] = set()
    for component in product_components(pid, component_map):
        for prop in component.properties:
            if prop in seen:
                continue
            seen.add(prop)
            props.append(prop)
    for component in product_projectable_global_components(pid, component_map):
        for prop in component.properties:
            if prop in seen:
                continue
            seen.add(prop)
            props.append(prop)
    return tuple(props)


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


def _expanded_component_names(spec: IoTProductSpec) -> tuple[str, ...]:
    if spec.normal_component_counts:
        return tuple(
            name
            for component_name in spec.normal_components
            for name in _repeat_component_name(spec, component_name)
        )
    if len(spec.normal_components) == 1 and (count := _fixed_component_count(spec)):
        return tuple(spec.normal_components[0] for _ in range(count))
    return spec.normal_components


def _repeat_component_name(spec: IoTProductSpec, component_name: str) -> tuple[str, ...]:
    count = _component_count(spec, component_name)
    return tuple(component_name for _ in range(count or 1))


def _component_count(spec: IoTProductSpec, component_name: str) -> int | None:
    for name, count in spec.normal_component_counts:
        if name == component_name and 0 < count <= 32:
            return count
    return None


def _fixed_component_count(spec: IoTProductSpec) -> int | None:
    count = to_int(spec.normal_component_count)
    if count is None or count < 2 or count > 32:
        return None
    return count


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
        "scene_panel",
    }:
        return component.category
    return component.platform_hint or component.category or component.alias


def _projectable_global_component(component: IoTComponentSpec) -> bool:
    """Return true for documented global components with safe HA projections."""
    return is_projectable_global_component(component)


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


def _range_value(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _component_key(value: Any) -> str:
    text = str(value).strip().lower()
    return " ".join(text.replace("_", " ").replace("-", " ").split())


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


__all__ = [
    "IOT_PRODUCT_SPECS",
    "is_projectable_global_component",
    "product_catalog",
    "product_category_candidates",
    "product_components",
    "product_hydration_properties",
    "product_projectable_global_components",
    "product_model_from_catalog",
    "product_protocols",
    "product_spec",
    "normalize_product_pid",
    "registry_property_model",
]
