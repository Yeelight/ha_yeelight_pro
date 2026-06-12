"""Capability evidence helpers for platform candidate ordering."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..core.device_registry_classification import registry_category_from_property_keys
from ..utils import to_category
from .platform_contract_data import RELAY_SWITCH_CONTROL_PROPS, SWITCH_IDENTITY_PROPS
from .registry import is_iot_category, parse_component_property_key


def capability_category(payload: Mapping[str, Any], props: set[str]) -> str | None:
    """Return the category implied by properties and structured components."""
    for component_category in component_categories(payload):
        category = registry_category_from_property_keys(
            props,
            current_category=component_category,
        )
        if category and category != "other":
            return category
    category = registry_category_from_property_keys(props)
    return category if category != "other" else None


def component_categories(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return structured component categories without top-level fallback."""
    categories: list[str] = []
    for subdevice in _rows(payload.get("subDeviceList")):
        _append_category(categories, subdevice.get("category"))
    product_model = payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        for component in components(product_model):
            _append_category(categories, component.get("category"))
    product_schema = payload.get("product_schema")
    if isinstance(product_schema, Mapping):
        for key in ("components", "customComponents"):
            for component in _rows(product_schema.get(key)):
                _append_category(categories, component.get("category"))
    return tuple(categories)


def has_light_capability_evidence(props: set[str]) -> bool:
    """Return true only for explicit light-control property combinations."""
    return bool(props & {"l", "ct", "c"}) or (
        "p" in props and bool(props & {"slisaon", "bp", "dd", "ct_rdy"})
    )


def has_switch_capability_evidence(
    category: str,
    props: set[str],
    has_indexed_switch: bool,
) -> bool:
    """Return true when switch evidence is stronger than generic power."""
    if props & SWITCH_IDENTITY_PROPS:
        return True
    return category == "relay_switch" and has_indexed_switch


def has_indexed_switch_control(payload: Mapping[str, Any], category: str) -> bool:
    """Return true for relay switch payloads with explicit indexed control keys."""
    if category != "relay_switch":
        return False
    params = payload.get("params")
    if not isinstance(params, Mapping):
        return False
    for key in params:
        try:
            control_key = parse_component_property_key(key)
        except ValueError:
            continue
        if control_key.component_index is not None and (
            control_key.prop_name in RELAY_SWITCH_CONTROL_PROPS
        ):
            return True
    return False


def components(product_model: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Return product-model component rows."""
    return _rows(product_model.get("components"))


def _append_category(categories: list[str], value: Any) -> None:
    category = to_category(value)
    if (
        category
        and is_iot_category(category)
        and category not in {"other", "gateway"}
        and category not in categories
    ):
        categories.append(category)


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


__all__ = [
    "capability_category",
    "component_categories",
    "components",
    "has_indexed_switch_control",
    "has_light_capability_evidence",
    "has_switch_capability_evidence",
]
