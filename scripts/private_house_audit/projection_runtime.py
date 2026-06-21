"""Runtime lookup helpers for private-house projection audits."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from custom_components.yeelight_pro.capabilities.registry import (
    parse_component_property_key,
)
from custom_components.yeelight_pro.utils import to_int, to_str


def runtime_property_keys(payload: Mapping[str, Any]) -> frozenset[tuple[str, str]]:
    """Return component/property pairs that have current runtime state evidence."""
    keys: set[tuple[str, str]] = set()
    _add_flat_runtime_keys(keys, payload.get("params"))
    _add_raw_property_rows(keys, payload.get("properties"))
    for subdevice in mapping_list(payload.get("subDeviceList")):
        index = to_str(subdevice.get("index"))
        _add_raw_property_rows(keys, subdevice.get("properties"), component_id=index)
    device_instance = payload.get("ha_device_instance")
    if isinstance(device_instance, Mapping):
        for component in mapping_list(device_instance.get("components")):
            component_id = to_str(
                component.get("component_id") or component.get("componentId")
            )
            state = component.get("state")
            if isinstance(state, Mapping):
                for prop_id in state:
                    _add_runtime_key(keys, component_id, to_str(prop_id))
    return frozenset(keys)


def schema_gap_reason(payload: Mapping[str, Any]) -> str | None:
    """Return schema absence reason separately from projection coverage."""
    if isinstance(payload.get("product_schema"), Mapping):
        return None
    if isinstance(payload.get("ha_product_model"), Mapping):
        return None
    if to_int(payload.get("pid")) is None:
        return "missing_pid"
    return "schema_endpoint_empty"


def safe_param_keys(payload: Mapping[str, Any], *, limit: int = 24) -> list[str]:
    """Return bounded runtime property keys for capability diagnosis."""
    params = payload.get("params")
    if not isinstance(params, Mapping):
        return []
    return sorted(str(key) for key in params)[:limit]


def device_name(payload: Mapping[str, Any]) -> str:
    """Return a human-readable device name from public metadata."""
    for key in ("name", "deviceName", "resourceName", "model", "type"):
        value = to_str(payload.get(key))
        if value:
            return value
    info = payload.get("device_info")
    if isinstance(info, Mapping):
        value = to_str(info.get("name"))
        if value:
            return value
    return "Unnamed device"


def device_category(payload: Mapping[str, Any]) -> str:
    """Return low-cardinality category for report grouping."""
    for key in ("iot_specific_category", "effective_category", "iot_category", "category"):
        value = to_str(payload.get(key))
        if value:
            return value
    return "unknown"


def online(payload: Mapping[str, Any]) -> bool | None:
    """Return optional online state."""
    value = payload.get("online")
    if isinstance(value, bool):
        return value
    return None


def stable_digest(value: Any) -> str:
    """Return a short stable digest for sensitive identifiers."""
    return hashlib.blake2b(str(value).encode("utf-8"), digest_size=8).hexdigest()


def model_property_ids(payload: Mapping[str, Any]) -> frozenset[str]:
    """Return property ids declared by the current payload model/schema."""
    values: set[str] = set()
    product_model = payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        for component in mapping_list(product_model.get("components")):
            for prop in mapping_list(component.get("properties")):
                prop_id = to_str(prop.get("prop_id") or prop.get("propId"))
                if prop_id:
                    values.add(prop_id)
    product_schema = payload.get("product_schema")
    if isinstance(product_schema, Mapping):
        for component in mapping_list(product_schema.get("components")):
            for prop in mapping_list(component.get("properties")):
                prop_id = to_str(prop.get("prop_id") or prop.get("propId"))
                if prop_id:
                    values.add(prop_id)
    return frozenset(values)


def instance_components_by_id(
    payload: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    """Return canonical component payload rows keyed by component id."""
    device_instance = payload.get("ha_device_instance")
    if not isinstance(device_instance, Mapping):
        return {}
    return {
        str(component.get("component_id") or component.get("componentId")): component
        for component in mapping_list(device_instance.get("components"))
    }


def mapping_list(value: Any) -> list[Mapping[str, Any]]:
    """Return mapping rows from a list-like value."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _add_flat_runtime_keys(
    keys: set[tuple[str, str]],
    values: Any,
) -> None:
    """Add runtime keys from flat params-like mappings."""
    if not isinstance(values, Mapping):
        return
    for raw_key in values:
        text = to_str(raw_key)
        if not text:
            continue
        parsed = parse_component_property_key(text)
        component_id = (
            str(parsed.component_index)
            if parsed.component_index is not None
            else ""
        )
        _add_runtime_key(keys, component_id, parsed.prop_name)


def _add_raw_property_rows(
    keys: set[tuple[str, str]],
    rows: Any,
    *,
    component_id: str | None = None,
) -> None:
    """Add runtime keys from Open API property row lists."""
    for prop in mapping_list(rows):
        prop_id = to_str(prop.get("propId") or prop.get("prop_id"))
        _add_runtime_key(keys, component_id, prop_id)


def _add_runtime_key(
    keys: set[tuple[str, str]],
    component_id: str | None,
    prop_id: str | None,
) -> None:
    """Add both precise and component-agnostic lookup keys."""
    if not prop_id:
        return
    component = component_id or ""
    keys.add((component, prop_id))
    keys.add(("", prop_id))
