"""Shared identity rules for Yeelight Pro event projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .utils import matches_category, to_category

SAFETY_EVENT_COMPONENT_ID = "safety_alarm"
SAFETY_EVENT_TYPES = ("power_alarm", "power_normal")
SAFETY_SENSOR_TOKENS = (
    "烟雾",
    "烟感",
    "smoke",
)


def is_safety_event_device(device_payload: Mapping[str, Any] | None) -> bool:
    """Return whether a payload is clearly a safety alarm event source."""
    if not isinstance(device_payload, Mapping):
        return False
    return matches_category(_identity_tokens(device_payload), SAFETY_SENSOR_TOKENS)


def is_safety_event_type(event_type: str | None) -> bool:
    """Return whether an event type is one of the documented alarm events."""
    return event_type in SAFETY_EVENT_TYPES


def _identity_tokens(device_payload: Mapping[str, Any]) -> str:
    """Combine device and product labels used for conservative identity checks."""
    product_model = device_payload.get("ha_product_model")
    product_payload = product_model.get("product") if isinstance(product_model, Mapping) else {}
    if not isinstance(product_payload, Mapping):
        product_payload = {}

    return " ".join(
        value
        for value in (
            to_category(device_payload.get("iot_category")),
            to_category(device_payload.get("category")),
            to_category(device_payload.get("type")),
            to_category(device_payload.get("name")),
            to_category(device_payload.get("deviceName")),
            to_category(device_payload.get("device_name")),
            to_category(device_payload.get("n")),
            to_category(device_payload.get("model")),
            to_category(device_payload.get("modelName")),
            to_category(device_payload.get("productName")),
            to_category(product_payload.get("category")),
            to_category(product_payload.get("model")),
            to_category(product_payload.get("name")),
        )
        if value
    )


__all__ = [
    "SAFETY_EVENT_COMPONENT_ID",
    "SAFETY_EVENT_TYPES",
    "is_safety_event_device",
    "is_safety_event_type",
]
