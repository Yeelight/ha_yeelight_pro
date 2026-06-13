"""Device-registry source id helpers for Yeelight Pro."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .const import DOMAIN


def source_device_ids(
    device_payload: Mapping[str, Any],
    identifiers: Iterable[tuple[str, str]],
) -> set[str]:
    """Return source device ids that may appear in entity unique_ids."""
    source_ids: set[str] = set()
    for key in ("device_id", "deviceId", "id"):
        value = device_payload.get(key)
        if value is not None:
            source_ids.add(str(value))
    for domain, identifier in identifiers:
        if domain != DOMAIN:
            continue
        text = str(identifier)
        marker = ":device:"
        if marker in text:
            source_ids.add(text.rsplit(marker, 1)[-1])
        elif text.startswith("device:"):
            source_ids.add(text.removeprefix("device:"))
    return {value for value in source_ids if value}


def source_device_id_from_unique_id(unique_id: str) -> str | None:
    """Extract Yeelight source device id from a device-backed unique_id."""
    prefix = f"{DOMAIN}_"
    if not unique_id.startswith(prefix):
        return None
    remainder = unique_id[len(prefix):]
    marker = "_device_"
    if marker in remainder:
        candidate = remainder.rsplit(marker, 1)[-1].split("_", 1)[0]
        return candidate if candidate.isdigit() else None
    source_device_id = remainder.split("_", 1)[0]
    return source_device_id if source_device_id.isdigit() else None


__all__ = ["source_device_id_from_unique_id", "source_device_ids"]
