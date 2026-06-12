"""Resolve Yeelight firmware metadata from documented runtime properties."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..capabilities.registry import parse_component_property_key
from ..utils import to_str

_FIRMWARE_VERSION_KEYS = (
    "sw_version",
    "swVersion",
    "firmwareVersion",
    "firmware_version",
    "fv",
)


def firmware_version(payload: Mapping[str, Any]) -> str | None:
    """Return firmware version from documented Yeelight ``fv`` property evidence."""
    if version := _first_text(payload, _FIRMWARE_VERSION_KEYS):
        return version

    params = payload.get("params")
    if isinstance(params, Mapping):
        for key, value in params.items():
            if _property_name(key) == "fv" and (version := to_str(value)):
                return version

    for prop in _property_rows(payload.get("properties")):
        if _property_name(_property_id(prop)) == "fv":
            value = prop.get("value", prop.get("data"))
            if version := to_str(value):
                return version

    instance = payload.get("ha_device_instance")
    if isinstance(instance, Mapping):
        for component in _property_rows(instance.get("components")):
            state = component.get("state")
            if isinstance(state, Mapping) and (version := to_str(state.get("fv"))):
                return version
    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if value := to_str(payload.get(key)):
            return value
    return None


def _property_rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _property_id(prop: Mapping[str, Any]) -> Any:
    return prop.get("prop_id", prop.get("propId", prop.get("propName")))


def _property_name(value: Any) -> str:
    text = to_str(value)
    if not text:
        return ""
    try:
        return parse_component_property_key(text).prop_name
    except ValueError:
        return text


__all__ = ["firmware_version"]
