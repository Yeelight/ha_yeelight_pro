"""Safety rules for registry-backed sensor platform evidence."""

from __future__ import annotations

from typing import Any

from .models import IoTPropertySpec
from .platform_contract_data import READ_ONLY_BOOL_BINARY_PROPS
from .registry import normalize_alias_key

SAFE_SCALAR_SENSOR_TYPES = frozenset({
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
SENSITIVE_SENSOR_TOKENS = frozenset({
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
APP_INTERNAL_PROPS = frozenset({"3rdPartySyncBitmask", "icon", "io", "io_type", "name"})
MAIN_ENTITY_SENSOR_EXCLUDED_PROPS = frozenset({
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
    if prop in APP_INTERNAL_PROPS:
        return False
    if prop in MAIN_ENTITY_SENSOR_EXCLUDED_PROPS or prop in READ_ONLY_BOOL_BINARY_PROPS:
        return False
    if not _safe_scalar_type(spec.data_type):
        return False
    normalized = normalize_alias_key(f"{prop} {spec.full_name} {spec.description or ''}")
    return not any(token in normalized for token in SENSITIVE_SENSOR_TOKENS)


def _safe_scalar_type(value: Any) -> bool:
    """Return true for scalar IoT data types that HA can display safely."""
    return str(value or "").strip().lower() in SAFE_SCALAR_SENSOR_TYPES


__all__ = [
    "APP_INTERNAL_PROPS",
    "MAIN_ENTITY_SENSOR_EXCLUDED_PROPS",
    "SAFE_SCALAR_SENSOR_TYPES",
    "SENSITIVE_SENSOR_TOKENS",
    "safe_registry_sensor_property",
]
