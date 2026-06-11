"""Helpers for resolving Yeelight source device ids for HA entities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def source_device_id(
    device_key: Any,
    device_payload: Mapping[str, Any],
) -> int | str:
    """Return the stable Yeelight id used for coordinator device lookup."""
    for key in ("device_id", "id", "deviceId", "did"):
        value = device_payload.get(key)
        if value not in (None, ""):
            return _normalize_device_id(value)
    return _normalize_device_id(device_key)


def _normalize_device_id(value: Any) -> int | str:
    """Prefer integer node ids while preserving non-numeric legacy ids."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


__all__ = ["source_device_id"]
