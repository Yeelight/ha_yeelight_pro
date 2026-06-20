"""Property inventory helpers for private-house coverage audits."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from custom_components.yeelight_pro.capabilities.registry import property_spec
from custom_components.yeelight_pro.utils import to_str


def property_inventory(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return product-model and instance property facts independent of HA registry."""
    product_model = payload.get("ha_product_model")
    device_instance = payload.get("ha_device_instance")
    components = _mapping_list(
        product_model.get("components") if isinstance(product_model, Mapping) else None
    )
    schema_property_keys = _schema_property_keys(payload)
    instance_components = _mapping_list(
        device_instance.get("components") if isinstance(device_instance, Mapping) else None
    )
    readable: list[dict[str, Any]] = []
    writable: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    actions_count = 0
    properties_count = 0
    for component in components:
        component_id = to_str(component.get("component_id") or component.get("componentId")) or ""
        component_category = to_str(component.get("category")) or ""
        for prop in _mapping_list(component.get("properties")):
            prop_id = to_str(prop.get("prop_id") or prop.get("propId")) or ""
            if not prop_id:
                continue
            properties_count += 1
            schema_property = (component_id, prop_id) in schema_property_keys
            item = {
                "component_id": component_id,
                "component_category": component_category,
                "prop_id": prop_id,
                "access": to_str(prop.get("access")) or "",
                "type": to_str(
                    prop.get("property_type")
                    or prop.get("propertyType")
                    or prop.get("kind")
                    or prop.get("format")
                )
                or "",
                "documented": property_spec(prop_id) is not None,
                "schema_property": schema_property,
            }
            if _access_allows_read(prop.get("access")):
                readable.append(item)
            if _access_allows_write(prop.get("access")):
                writable.append(item)
        for event in _mapping_list(component.get("events")):
            event_id = event.get("event_id", event.get("eventId"))
            events.append(
                {
                    "component_id": component_id,
                    "component_category": component_category,
                    "event_id": str(event_id) if event_id not in (None, "") else "",
                    "name": to_str(event.get("name")) or to_str(event.get("desc")) or "",
                }
            )
        actions_count += len(_mapping_list(component.get("actions")))
    device_actions = _mapping_list(
        product_model.get("device_actions", product_model.get("deviceActions"))
        if isinstance(product_model, Mapping)
        else None
    )
    actions_count += len(device_actions)
    return {
        "model_components_count": len(components),
        "model_properties_count": properties_count,
        "readable_properties": readable,
        "writable_properties": writable,
        "events": events,
        "model_actions_count": actions_count,
        "instance_components_count": len(instance_components),
        "instance_state_keys_count": sum(
            len(component.get("state") or {})
            for component in instance_components
            if isinstance(component.get("state"), Mapping)
        ),
    }


def _schema_property_keys(payload: Mapping[str, Any]) -> frozenset[tuple[str, str]]:
    """Return component/property pairs that came from a real product schema."""
    product_schema = payload.get("product_schema")
    if not isinstance(product_schema, Mapping):
        return frozenset()
    values: set[tuple[str, str]] = set()
    for component in _mapping_list(product_schema.get("components")):
        component_id = to_str(
            component.get("component_id") or component.get("componentId")
        ) or ""
        for prop in _mapping_list(component.get("properties")):
            prop_id = to_str(prop.get("prop_id") or prop.get("propId"))
            if prop_id:
                values.add((component_id, prop_id))
    return frozenset(values)


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    """Return mapping rows from a list-like value."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _access_allows_read(value: Any) -> bool:
    """Return whether schema access text allows reading."""
    text = (to_str(value) or "").lower()
    return any(token in text for token in ("read", "读", "r"))


def _access_allows_write(value: Any) -> bool:
    """Return whether schema access text allows writing."""
    text = (to_str(value) or "").lower()
    return any(token in text for token in ("write", "写", "w"))


__all__ = ["property_inventory"]
