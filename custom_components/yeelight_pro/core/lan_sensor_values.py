"""LAN sensor value normalization helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..utils import to_int

LAN_TEMPERATURE_HUMIDITY_TYPE = 136
LAN_TEMPERATURE_HUMIDITY_SCALE = 100


def normalize_lan_device_params(
    params: Mapping[str, Any],
    *,
    lan_type: Any,
) -> dict[str, Any]:
    """Normalize documented LAN device params before merging into runtime state."""
    normalized = dict(params)
    if to_int(lan_type) != LAN_TEMPERATURE_HUMIDITY_TYPE:
        return normalized

    if "t" in normalized:
        normalized["t"] = _normalize_temperature_humidity_value(normalized["t"])
    return normalized


def _normalize_temperature_humidity_value(value: Any) -> Any:
    """Convert type=136 raw integer temperature to Celsius."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value / LAN_TEMPERATURE_HUMIDITY_SCALE
    if isinstance(value, str):
        text = value.strip()
        raw = to_int(text)
        if raw is not None and text == str(raw):
            return raw / LAN_TEMPERATURE_HUMIDITY_SCALE
    return value


__all__ = [
    "LAN_TEMPERATURE_HUMIDITY_SCALE",
    "LAN_TEMPERATURE_HUMIDITY_TYPE",
    "normalize_lan_device_params",
]
