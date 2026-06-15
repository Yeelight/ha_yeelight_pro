"""Yeelight IoT 产品构成目录查询与模型构建."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

from ..canonical.models import HAProductModel
from ..utils import to_int
from .models import IoTComponentSpec, IoTProductSpec
from .product_catalog_model import (
    build_product_model,
    registry_property_model,
)
from .product_catalog_data import (
    IOT_MD_ONLY_COMPONENT_SPECS,
    IOT_MD_ONLY_PRODUCT_SPECS,
    IOT_PRODUCT_SPECS,
)

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
    """返回 pid -> 产品构成定义，包含 CSV 主表和 LAN 文档补充产品."""
    return {item.pid: item for item in (*IOT_PRODUCT_SPECS, *IOT_MD_ONLY_PRODUCT_SPECS)}


@lru_cache(maxsize=1)
def csv_product_catalog() -> dict[int, IoTProductSpec]:
    """返回基础信息_产品构成.csv 固化的 pid -> 产品定义."""
    return {item.pid: item for item in IOT_PRODUCT_SPECS}


@lru_cache(maxsize=1)
def md_only_product_catalog() -> dict[int, IoTProductSpec]:
    """返回 LAN Markdown 文档补充的 pid -> 产品定义."""
    return {item.pid: item for item in IOT_MD_ONLY_PRODUCT_SPECS}


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
    local_component_map = _product_component_map(component_map)
    for name in _expanded_component_names(spec):
        component = local_component_map.get(_component_key(name))
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
    return build_product_model(
        spec,
        catalog_components,
        product_protocols(spec.pid),
        property_builder,
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


def _projectable_global_component(component: IoTComponentSpec) -> bool:
    """Return true for documented global components with safe HA projections."""
    return is_projectable_global_component(component)


def _component_key(value: Any) -> str:
    text = str(value).strip().lower()
    return " ".join(text.replace("_", " ").replace("-", " ").split())


def _product_component_map(
    component_map: dict[str, IoTComponentSpec],
) -> dict[str, IoTComponentSpec]:
    """返回包含产品级补充组件的组件索引."""
    if not IOT_MD_ONLY_COMPONENT_SPECS:
        return component_map
    merged = dict(component_map)
    for component in IOT_MD_ONLY_COMPONENT_SPECS:
        for key in (component.alias, component.name, component.component_id):
            merged[_component_key(key)] = component
    return merged


__all__ = [
    "IOT_MD_ONLY_COMPONENT_SPECS",
    "IOT_MD_ONLY_PRODUCT_SPECS",
    "IOT_PRODUCT_SPECS",
    "csv_product_catalog",
    "md_only_product_catalog",
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
