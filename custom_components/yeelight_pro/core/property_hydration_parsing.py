"""Response parsing helpers for Yeelight property hydration."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..utils import to_int, to_str

def _parse_indexed_node_property_response(
    response: Mapping[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    """Parse a single-node indexed read response into runtime ``N-prop`` values."""
    result = _node_read_result(response)
    if result is None:
        return {}
    code = to_str(result.get("code"))
    if code not in {None, "", "200"}:
        return {}
    values = _property_values(result.get("data"))
    return {
        _ensure_indexed_property_key(prop, index): value
        for prop, value in values.items()
    }


def _ensure_indexed_property_key(prop: str, index: int) -> str:
    """Prefix a property id with the requested sub-device index when needed."""
    if "-" in prop and prop.split("-", 1)[0].isdecimal():
        return prop
    return f"{index}-{prop}"

def _property_has_value(item: Mapping[str, Any]) -> bool:
    """Return true when an OpenAPI property row already carries a live value."""
    return item.get("value") is not None or item.get("data") is not None


def _parse_multi_node_property_response(response: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Parse documented 3.2.7 response variants into values by resource id."""
    raw_data = response.get("data")
    if not isinstance(raw_data, (Mapping, list)):
        return {}

    parsed: dict[str, dict[str, Any]] = {}
    for resource_id, result in _node_property_results(raw_data):
        result = _node_read_result(result)
        if result is None:
            continue
        code = to_str(result.get("code"))
        if code not in {None, "", "200"}:
            continue
        values = _property_values(result.get("data"))
        if values:
            parsed[str(resource_id)] = values
    return parsed


def _node_property_results(
    raw_data: Mapping[str, Any] | list[Any],
) -> Iterable[tuple[Any, Any]]:
    """Yield resource ids and read results from map or list response shapes."""
    if isinstance(raw_data, Mapping):
        yield from raw_data.items()
        return
    for item in raw_data:
        if not isinstance(item, Mapping):
            continue
        resource_id = item.get("resId", item.get("id", item.get("resourceId")))
        if resource_id is None:
            continue
        yield resource_id, item


def _node_read_result(value: Any) -> Mapping[str, Any] | None:
    """Return one node read result, unwrapping list-row response variants."""
    if not isinstance(value, Mapping):
        return None
    data = value.get("data")
    if (
        "code" not in value
        and isinstance(data, Mapping)
        and ("code" in data or "data" in data)
    ):
        return data
    return value


def _property_values(value: Any) -> dict[str, Any]:
    """Return property values from read API item shapes."""
    values: dict[str, Any] = {}
    for item in _property_list(value):
        prop = _indexed_property_id(item)
        if not prop:
            continue
        if "value" in item:
            values[prop] = item.get("value")
        elif "data" in item:
            values[prop] = item.get("data")
    return values


def _existing_property_ids(device: Mapping[str, Any]) -> set[str]:
    """Return property ids already advertised by a device row."""
    props = {_property_id(item) for item in _property_list(device.get("properties"))}
    for subdevice in _property_list(device.get("subDeviceList")):
        props.update(_property_id(item) for item in _property_list(subdevice.get("properties")))
    raw_params = device.get("params")
    if isinstance(raw_params, Mapping):
        props.update(str(key).split("-", 1)[-1] for key in raw_params)
    return {prop for prop in props if prop}


def _schema_property_ids(schema: Mapping[str, Any]) -> set[str]:
    """Return property ids from a product schema."""
    props: set[str] = set()
    for key in ("components", "customComponents"):
        for component in _property_list(schema.get(key)):
            props.update(
                prop
                for prop in (_property_id(item) for item in _property_list(component.get("properties")))
                if prop
            )
    return props


def _device_id(device: Mapping[str, Any]) -> int | str | None:
    """Return an Open API device id from common row variants."""
    value = device.get("id", device.get("device_id"))
    if value is None:
        value = device.get("deviceId")
    return value if value is not None and str(value) else None


def _property_list(value: Any) -> list[Mapping[str, Any]]:
    """Return only mapping items from an API list field."""
    return [item for item in value or [] if isinstance(item, Mapping)]


def _property_id(item: Mapping[str, Any]) -> str | None:
    """Return the property id/name from API variants."""
    return to_str(item.get("propId", item.get("propName")))


def _indexed_property_id(item: Mapping[str, Any]) -> str | None:
    """Return a prop id, preserving documented sub-device ``index`` when present."""
    prop = _property_id(item)
    if prop is None:
        return None
    index = to_int(item.get("index"))
    if index is None:
        return prop
    return f"{index}-{prop}"
