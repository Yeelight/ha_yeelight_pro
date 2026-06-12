"""Event-input identity helpers for Yeelight projector modules."""

from __future__ import annotations

from typing import Any, Mapping

from ..capabilities.registry import iot_registry
from ..utils import to_category, to_int, to_str

EVENT_INPUT_CATEGORIES = frozenset({"scene_panel", "knob_switch"})
EVENT_STYLE_PRODUCT_TYPES = frozenset({128, 132})
_EVENT_STYLE_PRODUCT_TYPE_CATEGORIES: dict[int, str] = {
    128: "scene_panel",
    132: "knob_switch",
}


def is_event_input_category(value: Any) -> bool:
    """Return true only for documented event-input IoT categories."""
    return _category_key(value) in EVENT_INPUT_CATEGORIES


def is_event_input_component(value: Any) -> bool:
    """Return true when a component identity maps to an event-input category."""
    return event_input_component_category(value) is not None


def is_event_input_component_context(category: Any, component_id: Any) -> bool:
    """Return true for a component category/id pair that is event-only."""
    return (
        is_event_input_category(category)
        or is_event_input_component(category)
        or is_event_input_component(component_id)
    )


def event_input_component_category(value: Any) -> str | None:
    """Return the documented event-input category for a component identity."""
    spec = iot_registry().component_map.get(_component_key(value))
    if spec is not None and spec.category in EVENT_INPUT_CATEGORIES:
        return spec.category
    return None


def event_input_category_for_device(device_payload: Mapping[str, Any]) -> str | None:
    """Return the documented event-input category for a device payload."""
    product_type = to_int(device_payload.get("product_type"))
    product_type_category = (
        _EVENT_STYLE_PRODUCT_TYPE_CATEGORIES.get(product_type)
        if product_type is not None
        else None
    )
    if product_type_category is not None:
        return product_type_category

    for key in ("iot_category", "category"):
        category = _category_key(device_payload.get(key))
        if category in EVENT_INPUT_CATEGORIES:
            return category

    product_model = device_payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        product = product_model.get("product")
        if isinstance(product, Mapping):
            category = _category_key(product.get("category"))
            if category in EVENT_INPUT_CATEGORIES:
                return category
            categories = product.get("categories")
            if isinstance(categories, list):
                for item in categories:
                    category = _category_key(item)
                    if category in EVENT_INPUT_CATEGORIES:
                        return category
        allow_names = _product_model_has_official_component_names(product_model)
        for component in _rows(product_model.get("components")):
            component_category = _event_input_category_from_component(
                component,
                allow_names=allow_names,
            )
            if component_category is not None:
                return component_category

    instance = device_payload.get("ha_device_instance")
    if isinstance(instance, Mapping):
        for component in _rows(instance.get("components")):
            component_category = _event_input_category_from_runtime_component(component)
            if component_category is not None:
                return component_category

    return None


def is_event_input_device(device_payload: Mapping[str, Any]) -> bool:
    """Return true for documented scene-panel or knob event-input devices."""
    return event_input_category_for_device(device_payload) is not None


def _event_input_category_from_component(
    component: Mapping[str, Any],
    *,
    allow_names: bool,
) -> str | None:
    category = _category_key(component.get("category"))
    if category in EVENT_INPUT_CATEGORIES:
        return category
    keys = ("category", "cid", "component_id", "name", "desc") if allow_names else (
        "category",
        "cid",
        "component_id",
    )
    for key in keys:
        component_category = event_input_component_category(component.get(key))
        if component_category is not None:
            return component_category
    return None


def _event_input_category_from_runtime_component(component: Mapping[str, Any]) -> str | None:
    category = _category_key(component.get("category"))
    if category in EVENT_INPUT_CATEGORIES:
        return category
    for key in ("category", "cid", "component_id"):
        component_category = event_input_component_category(component.get(key))
        if component_category is not None:
            return component_category
    return None


def _product_model_has_official_component_names(product_model: Mapping[str, Any]) -> bool:
    """Return true when component names come from product docs, not runtime rows."""
    schema_version = to_str(product_model.get("schema_version") or product_model.get("schemaVersion"))
    return schema_version != "runtime-v1"


def _component_key(value: Any) -> str:
    text = to_str(value)
    if not text:
        return ""
    return " ".join(text.lower().replace("_", " ").replace("-", " ").split())


def _category_key(value: Any) -> str:
    return to_category(value).replace("-", "_").replace(" ", "_")


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


__all__ = [
    "EVENT_INPUT_CATEGORIES",
    "EVENT_STYLE_PRODUCT_TYPES",
    "event_input_category_for_device",
    "event_input_component_category",
    "is_event_input_category",
    "is_event_input_component",
    "is_event_input_component_context",
    "is_event_input_device",
]
