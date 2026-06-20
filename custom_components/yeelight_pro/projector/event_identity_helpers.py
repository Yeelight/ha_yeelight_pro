"""Yeelight Pro event identity and registry matching helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping

from ..canonical.models import ComponentModel, HAProductModel
from ..capabilities.events import normalize_event_type
from ..capabilities.registry import iot_registry
from ..utils import to_category, to_str
from .event_input import (
    event_input_category_for_device,
    event_input_component_category,
    is_event_input_category,
)


def event_types(component: ComponentModel) -> list[str]:
    """提取组件的规范化事件类型列表。"""
    projected: list[str] = []
    seen: set[str] = set()
    registry_event_types = {event.normalized for event in iot_registry().events}
    for event in component.events:
        event_type = _registry_event_type(event.event_id, registry_event_types)
        if event_type is None:
            event_type = (
                _registry_event_type(event.semantic, registry_event_types)
                or _registry_event_type(event.name, registry_event_types)
                or _registry_event_type(event.desc, registry_event_types)
            )
        if not event_type or event_type in seen:
            continue
        seen.add(event_type)
        projected.append(event_type)
    return projected


def _registry_event_type(
    value: Any,
    registry_event_types: set[str],
) -> str | None:
    """Return a registry-known event type without accepting unknown display names."""
    event_type = normalize_event_type(value)
    if event_type in registry_event_types:
        return event_type
    return None


def fallback_event_input_category(
    device_payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> str | None:
    """Return fallback event-input category from documented identity only."""
    if category := event_input_category_for_device(device_payload):
        return category
    return product_event_input_category(product_model)


def event_input_category(
    component: ComponentModel,
    product_model: HAProductModel,
) -> str | None:
    """Return documented event-input category for a schema component."""
    for value in (
        component.category,
        component.cid,
        component.component_id,
        *(
            (component.name, component.desc)
            if product_model_has_official_component_names(product_model)
            else ()
        ),
    ):
        category = category_key(value)
        if is_event_input_category(category):
            return category
        if component_category := event_input_component_category(value):
            return component_category
    return product_event_input_category(product_model)


def product_event_input_category(product_model: HAProductModel) -> str | None:
    """Return documented event-input category from product metadata."""
    category = category_key(product_model.product.category)
    if is_event_input_category(category):
        return category
    for item in product_model.product.categories:
        category = category_key(item)
        if is_event_input_category(category):
            return category
    return None


def has_registry_supported_events(
    component: ComponentModel,
    product_model: HAProductModel,
) -> bool:
    """判断组件 schema 事件是否属于 registry 明确支持的组件关系。"""
    component_keys = registry_component_keys(
        component,
        allow_names=product_model_has_official_component_names(product_model),
    )
    if not component_keys:
        return False

    registry = iot_registry()
    for event_type in event_types(component):
        event_spec = next(
            (event for event in registry.events if event.normalized == event_type),
            None,
        )
        if event_spec is None:
            continue
        for component_alias in event_spec.components:
            if normalize_component_alias(component_alias) in component_keys:
                return True
    return False


def has_known_registry_events(component: ComponentModel) -> bool:
    """判断组件 schema 是否声明了 registry 已知事件类型。"""
    registry_event_types = {event.normalized for event in iot_registry().events}
    return any(event_type in registry_event_types for event_type in event_types(component))


def event_identity_tokens(component: ComponentModel, product_model: HAProductModel) -> str:
    """合并 event 推断需要的组件与产品身份 token。"""
    return " ".join(
        value
        for value in (
            to_category(component.category),
            component.component_id.lower(),
            to_category(product_model.product.category),
        )
        if value
    )


def registry_component_keys(
    component: ComponentModel,
    *,
    allow_names: bool,
) -> set[str]:
    """返回用于匹配 registry 组件别名的规范化身份集合。"""
    keys = {
        key
        for key in (
            normalize_component_alias(component.component_id),
            normalize_component_alias(component.category),
            normalize_component_alias(component.cid),
        )
        if key
    }
    # 官方产品 schema/catalog 可能只用文档组件名表达身份；runtime 推断的
    # 子设备 name/desc 是用户可见标签，不能参与类型判定。
    if allow_names:
        keys.update(
            key
            for key in (
                normalize_component_alias(component.name),
                normalize_component_alias(component.desc),
            )
            if key
        )
    registry = iot_registry()
    for key in tuple(keys):
        spec = registry.component_map.get(key)
        if spec is None:
            continue
        keys.update(
            key
            for key in (
                normalize_component_alias(spec.alias),
                normalize_component_alias(spec.name),
                normalize_component_alias(spec.component_id),
            )
            if key
        )
    return keys


def product_model_has_official_component_names(product_model: HAProductModel) -> bool:
    """Return true when component names come from product docs, not runtime rows."""
    return product_model.schema_version != "runtime-v1"


def normalize_component_alias(value: Any) -> str:
    """归一化组件别名，兼容英文、中文、下划线和数字 id。"""
    text = to_str(value)
    if not text:
        return ""
    return re.sub(r"[\s_-]+", " ", text.lower()).strip()


def category_key(value: Any) -> str:
    """Normalize IoT category spelling without inspecting user device names."""
    return to_category(value).replace("-", "_").replace(" ", "_")
