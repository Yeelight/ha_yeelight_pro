"""Safety rules for registry-backed sensor projections."""

from __future__ import annotations

from typing import Any

from ..capabilities.platform_contract_data import READ_ONLY_BOOL_BINARY_PROPS
from ..capabilities.models import IoTPropertySpec
from ..capabilities.registry import normalize_alias_key

_SAFE_SCALAR_TYPES = frozenset({
    "bool",
    "boolean",
    "double",
    "enum",
    "float",
    "int",
    "int64",
    "integer",
    "string",
    "uint8",
    "uint16",
    "uint32",
})
_SENSITIVE_TOKENS = frozenset({
    "bind_key",
    "device_key",
    "did",
    "domain",
    "external_ip",
    "info",
    "ip",
    "key",
    "login",
    "mac",
    "password",
    "psk",
    "remote_management",
    "ssid",
    "token",
})
_APP_INTERNAL_PROPS = frozenset({"3rdPartySyncBitmask", "icon", "io", "io_type", "name"})
_MAIN_ENTITY_SENSOR_EXCLUDED_PROPS = frozenset({
    "acp",
    "actt",
    "acct",
    "c",
    "cp",
    "ct",
    "l",
    "m",
    "p",
    "rfhct",
    "rfhp",
    "rfhtt",
    "sp",
    "tgt",
    "tp",
    "vmcf",
    "vmcp",
})


def safe_registry_sensor_property(prop: str, spec: IoTPropertySpec | None) -> bool:
    """Return true when a documented property is safe as a HA sensor."""
    if spec is None or not spec.readable:
        return False
    if spec.category == "config" and spec.writable:
        return False
    if prop in _APP_INTERNAL_PROPS:
        return False
    if prop in _MAIN_ENTITY_SENSOR_EXCLUDED_PROPS or prop in READ_ONLY_BOOL_BINARY_PROPS:
        return False
    if not _safe_scalar_type(spec.data_type):
        return False
    normalized = normalize_alias_key(f"{prop} {spec.full_name} {spec.description or ''}")
    return not any(token in normalized for token in _SENSITIVE_TOKENS)


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


def _safe_scalar_type(value: Any) -> bool:
    """Return true for scalar IoT data types that HA can display safely."""
    return str(value or "").strip().lower() in _SAFE_SCALAR_TYPES


__all__ = [
    "registry_sensor_component_id",
    "registry_sensor_icon",
    "registry_sensor_label",
    "safe_registry_sensor_property",
]
