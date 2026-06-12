"""Compatibility facade for registry-backed sensor projection safety."""

from __future__ import annotations

from ..capabilities.models import IoTPropertySpec
from ..capabilities.registry import normalize_alias_key
from ..capabilities.sensor_safety import safe_registry_sensor_property


def registry_sensor_component_id(prop: str, spec: IoTPropertySpec) -> str:
    """Return a stable component id for a registry-backed sensor property."""
    base = normalize_alias_key(spec.full_name) or normalize_alias_key(spec.display_name)
    base = base or normalize_alias_key(prop)
    return base or "property"


def registry_sensor_label(prop: str, spec: IoTPropertySpec) -> str:
    """Return a concise user-facing sensor label."""
    return spec.display_name or prop


def registry_sensor_icon(prop: str, spec: IoTPropertySpec) -> str | None:
    """Return a generic icon for safe properties without HA device_class."""
    data_type = (spec.data_type or "").lower()
    if data_type in {"bool", "boolean"}:
        return "mdi:checkbox-marked-circle-outline"
    if data_type in {"enum", "string"}:
        return "mdi:information-outline"
    return "mdi:gauge"


__all__ = [
    "registry_sensor_component_id",
    "registry_sensor_icon",
    "registry_sensor_label",
    "safe_registry_sensor_property",
]
