"""Product-model inventory diagnostics for Yeelight Pro."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .capabilities.spec_correction import normalize_property_access


def spec_runtime_inventory_diagnostics(
    devices: list[Mapping[str, Any]],
) -> dict[str, int]:
    """Return aggregate runtime product-model inventory diagnostics."""
    totals = {
        "product_models_seen": 0,
        "unique_product_models_seen": 0,
        "components_seen": 0,
        "properties_seen": 0,
        "events_seen": 0,
        "event_params_seen": 0,
        "component_actions_seen": 0,
        "device_actions_seen": 0,
        "action_params_seen": 0,
        "readable_properties": 0,
        "writable_properties": 0,
    }
    model_ids: set[str] = set()
    for device in devices:
        product_model = device.get("ha_product_model")
        if not isinstance(product_model, Mapping):
            continue
        totals["product_models_seen"] += 1
        model_id = _product_model_id(product_model)
        if model_id is not None:
            model_ids.add(model_id)
        _add_component_inventory(totals, product_model)
        _add_device_action_inventory(totals, product_model)
    totals["unique_product_models_seen"] = len(model_ids)
    return totals


def _add_component_inventory(
    totals: dict[str, int],
    product_model: Mapping[str, Any],
) -> None:
    """Update inventory totals from product-model components."""
    for component in _mapping_items(product_model.get("components")):
        totals["components_seen"] += 1
        properties = _mapping_items(component.get("properties"))
        totals["properties_seen"] += len(properties)
        for prop in properties:
            readable, writable = _property_access_flags(prop)
            if readable:
                totals["readable_properties"] += 1
            if writable:
                totals["writable_properties"] += 1

        events = _mapping_items(component.get("events"))
        totals["events_seen"] += len(events)
        for event in events:
            totals["event_params_seen"] += len(_mapping_items(event.get("params")))

        actions = _mapping_items(component.get("actions"))
        totals["component_actions_seen"] += len(actions)
        for action in actions:
            totals["action_params_seen"] += len(_mapping_items(action.get("params")))


def _add_device_action_inventory(
    totals: dict[str, int],
    product_model: Mapping[str, Any],
) -> None:
    """Update inventory totals from product-model device-level actions."""
    device_actions = _mapping_items(
        product_model.get("device_actions", product_model.get("deviceActions"))
    )
    totals["device_actions_seen"] += len(device_actions)
    for action in device_actions:
        totals["action_params_seen"] += len(_mapping_items(action.get("params")))


def _mapping_items(value: Any) -> list[Mapping[str, Any]]:
    """Return mapping items from a list-like product model field."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _property_access_flags(prop: Mapping[str, Any]) -> tuple[bool, bool]:
    """Return readable/writable flags while preserving explicit write-only diagnostics."""
    access_text = _access_text(prop.get("access"))
    if access_text in {"write", "write_only", "writeonly", "wo", "w"}:
        return False, True
    access = normalize_property_access(prop.get("access"), prop.get("operators"))
    return access in {"read_only", "read_write"}, access == "read_write"


def _access_text(value: Any) -> str | None:
    """Return normalized access text for diagnostics-only compatibility checks."""
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _product_model_id(product_model: Mapping[str, Any]) -> str | None:
    """Return product model id for aggregate-only de-duplication."""
    product = product_model.get("product")
    if not isinstance(product, Mapping):
        return None
    value = product.get("model_id", product.get("modelId"))
    return str(value) if value is not None else None


__all__ = ["spec_runtime_inventory_diagnostics"]
