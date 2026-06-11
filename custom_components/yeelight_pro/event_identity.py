"""Shared identity rules for Yeelight Pro event projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SAFETY_EVENT_COMPONENT_ID = "safety_alarm"
SAFETY_EVENT_TYPES = ("power_alarm", "power_normal")


def is_safety_event_device(device_payload: Mapping[str, Any] | None) -> bool:
    """Return whether a payload is clearly a safety alarm event source."""
    if not isinstance(device_payload, Mapping):
        return False
    product_model = device_payload.get("ha_product_model")
    if not isinstance(product_model, Mapping):
        return False
    components = product_model.get("components")
    if not isinstance(components, list):
        return False
    return any(
        _component_declares_safety_event(component)
        for component in components
        if isinstance(component, Mapping)
    )


def is_safety_event_type(event_type: str | None) -> bool:
    """Return whether an event type is one of the documented alarm events."""
    return event_type in SAFETY_EVENT_TYPES


def _component_declares_safety_event(component: Mapping[str, Any]) -> bool:
    """Return true only when schema/runtime metadata declares alarm events."""
    events = component.get("events")
    if not isinstance(events, list):
        return False
    declared = {
        _event_type(event)
        for event in events
        if isinstance(event, Mapping)
    }
    return set(SAFETY_EVENT_TYPES).issubset(declared)


def _event_type(event: Mapping[str, Any]) -> str | None:
    from .capabilities.events import normalize_event_type

    return (
        normalize_event_type(event.get("semantic"))
        or normalize_event_type(event.get("name"))
        or normalize_event_type(event.get("desc"))
        or normalize_event_type(event.get("event_id", event.get("eventId")))
    )


__all__ = [
    "SAFETY_EVENT_COMPONENT_ID",
    "SAFETY_EVENT_TYPES",
    "is_safety_event_device",
    "is_safety_event_type",
]
