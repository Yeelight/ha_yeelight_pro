"""Rule parsing and matching helpers for Yeelight Pro device import filters."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

FILTER_DIMENSIONS = (
    "categories",
    "types",
    "rooms",
    "gateways",
    "product_ids",
    "devices",
)


def _normalize_text(value: Any) -> str:
    """Normalize option keys and enum-like fields for robust matching."""
    return str(value).strip().lower()


FILTER_DIMENSION_ALIASES = {
    "category": "categories",
    "categories": "categories",
    "device": "devices",
    "deviceId": "devices",
    "device_id": "devices",
    "devices": "devices",
    "gateway": "gateways",
    "gatewayDeviceId": "gateways",
    "gatewayId": "gateways",
    "gateway_id": "gateways",
    "gateways": "gateways",
    "nodeType": "types",
    "node_type": "types",
    "node_types": "types",
    "pid": "product_ids",
    "productID": "product_ids",
    "productId": "product_ids",
    "productKey": "product_ids",
    "product_id": "product_ids",
    "product_ids": "product_ids",
    "product_key": "product_ids",
    "room": "rooms",
    "roomId": "rooms",
    "roomIdList": "rooms",
    "roomIds": "rooms",
    "room_id": "rooms",
    "rooms": "rooms",
    "type": "types",
    "types": "types",
}
_FILTER_DIMENSION_LOOKUP = {
    _normalize_text(key): dimension
    for key, dimension in FILTER_DIMENSION_ALIASES.items()
}


def rules(value: Any) -> dict[str, set[str]]:
    """Normalize filter rules to dimension -> string set."""
    normalized_rules, _ = rules_with_ignored(value)
    return normalized_rules


def rules_with_ignored(value: Any) -> tuple[dict[str, set[str]], int]:
    """Normalize filter rules and count unsupported configured values."""
    if not isinstance(value, Mapping):
        return {}, 0
    normalized_rules: dict[str, set[str]] = {}
    ignored = 0
    for raw_dimension, raw_value in value.items():
        dimension = _FILTER_DIMENSION_LOOKUP.get(_normalize_text(raw_dimension))
        if dimension is None:
            ignored += len(_string_set(raw_value)) or 1
            continue
        items = _string_set(raw_value)
        if items:
            normalized_rules.setdefault(dimension, set()).update(items)
    return normalized_rules, ignored


def mode(value: Any) -> str:
    """Return supported rule aggregation mode."""
    return "and" if _normalize_text(value) == "and" else "or"


def normalize_bool(value: Any) -> bool:
    """Return a robust bool for legacy config-entry option values."""
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"false", "0", "no", "off", ""}:
            return False
        if normalized in {"true", "1", "yes", "on"}:
            return True
    return bool(value)


def stored_rules(rule_values: Mapping[str, set[str]]) -> dict[str, list[str]]:
    """Return sorted rule lists in canonical dimension order."""
    return {
        dimension: sorted(values)
        for dimension in FILTER_DIMENSIONS
        if (values := rule_values.get(dimension))
    }


def matches_rules(
    device: Mapping[str, Any],
    rule_values: Mapping[str, set[str]],
    *,
    mode: str,
) -> bool:
    """Return whether a device matches the configured rules."""
    if not rule_values:
        return False
    results = [
        bool(device_values(device, dimension) & expected)
        for dimension, expected in rule_values.items()
    ]
    return all(results) if mode == "and" else any(results)


def distinct_value_counts(
    devices: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    """Return diagnostics-safe distinct value counts by dimension."""
    counts: dict[str, int] = {}
    for dimension in FILTER_DIMENSIONS:
        values: set[str] = set()
        for device in devices:
            values.update(_diagnostic_device_values(device, dimension))
        if values:
            counts[dimension] = len(values)
    return counts


def device_values(device: Mapping[str, Any], dimension: str) -> set[str]:
    """Return comparable Yeelight device values for a filter dimension."""
    if dimension == "categories":
        return _values(device, "category")
    if dimension == "types":
        return _values(device, "type", "nodeType", "node_type")
    if dimension == "rooms":
        return _values(device, "roomId", "room_id", "roomIdList", "roomIds")
    if dimension == "gateways":
        return _values(device, "gatewayId", "gateway_id", "gatewayDeviceId")
    if dimension == "product_ids":
        return _values(
            device,
            "pid",
            "productId",
            "product_id",
            "productKey",
            "product_key",
        )
    if dimension == "devices":
        return _values(device, "id", "device_id", "deviceId")
    return set()


def _diagnostic_device_values(device: Mapping[str, Any], dimension: str) -> set[str]:
    """Return one diagnostics choice per device for high-cardinality dimensions."""
    if dimension == "devices":
        for key in ("device_id", "deviceId", "id"):
            value = device.get(key)
            if value is not None and str(value):
                return {str(value)}
        return set()
    return device_values(device, dimension)


def _string_set(value: Any) -> set[str]:
    """Normalize a scalar or iterable option into a set of strings."""
    if value is None:
        return set()
    if isinstance(value, str):
        return {
            item
            for raw_item in value.split(",")
            if (item := str(raw_item).strip())
        }
    if isinstance(value, Iterable):
        return {
            text
            for item in value
            if item is not None and (text := str(item).strip())
        }
    text = str(value).strip()
    return {text} if text else set()


def _values(device: Mapping[str, Any], *keys: str) -> set[str]:
    """Return non-empty string values for one or more payload keys."""
    values: set[str] = set()
    for key in keys:
        value = device.get(key)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
            values.update(
                text
                for item in value
                if item is not None and (text := str(item).strip())
            )
        elif value is not None and (text := str(value).strip()):
            values.add(text)
    return values
