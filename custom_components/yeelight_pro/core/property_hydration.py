"""Hydrate runtime device rows with documented Yeelight property reads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import logging
from typing import Any, Protocol

from ..utils import to_int, to_str
from ..capabilities.registry import product_hydration_properties
from .device_classification import infer_iot_category
from .device_runtime_capabilities import schema_conflicts_with_runtime_category
from .exceptions import AuthenticationError, safe_error_summary
from .property_hydration_summary import PropertyHydrationDiagnostics

_LOGGER = logging.getLogger(__name__)

DEFAULT_HYDRATION_PROPERTIES = (
    "p",
    "l",
    "ct",
    "c",
    "m",
    "sp",
    "mv",
    "dc",
    "alm",
    "luminance",
    "level",
    "t",
    "temp",
    "h",
    "bl",
    "bc",
    "bcg",
    "cp",
    "tp",
    "rd",
    "acp",
    "aco",
    "acm",
    "actt",
    "acct",
    "acf",
    "tgt",
    "fa",
    "he",
    "rfhp",
    "rfhct",
    "rfhtt",
    "curp",
    "iec",
    "ap",
    "ae",
    "o",
)

_CATEGORY_EXTRA_PROPERTIES: dict[str, tuple[str, ...]] = {
    "contact_sensor": ("dc", "alm", "bl", "bc", "bcg", "o"),
    "human_sensor": ("mv", "alm", "luminance", "bl", "bc", "bcg", "o"),
    "light_sensor": ("luminance", "level", "bl", "bc", "bcg", "o"),
    "curtain": ("cp", "tp", "rd", "o"),
    "temp_control": (
        "t",
        "temp",
        "tgt",
        "fa",
        "he",
        "acp",
        "aco",
        "acm",
        "actt",
        "acct",
        "acf",
        "rfhp",
        "rfhct",
        "rfhtt",
        "o",
    ),
    "relay_switch": ("p", "sp", "l", "o"),
    "light": ("p", "l", "ct", "c", "m", "o"),
    "scene_panel": ("o",),
    "knob_switch": ("o",),
    "other": ("t", "temp", "h", "luminance", "curp", "iec", "ap", "ae", "bl", "bc", "bcg", "o"),
}


class PropertyHydrationClient(Protocol):
    """Client protocol for documented multi-node property reads."""

    async def read_nodes_properties(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_ids: list[int | str],
        properties: list[str],
    ) -> dict[str, Any]:
        """Read multiple properties for multiple Open API nodes."""

    async def read_node_properties(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_id: int | str,
        properties: list[str],
        index: int | None = None,
    ) -> dict[str, Any]:
        """Read multiple properties for one Open API node."""


async def async_hydrate_device_properties(
    client: PropertyHydrationClient,
    *,
    house_id: int,
    devices: Sequence[Mapping[str, Any]],
    product_schemas: Mapping[int, Mapping[str, Any]] | None = None,
    diagnostics: PropertyHydrationDiagnostics | None = None,
) -> list[dict[str, Any]]:
    """Return device rows with missing property values filled from Open API.

    The device-list endpoint may omit ``properties`` values. Projectors depend on
    current property values, so this performs documented read-only
    multi-node/multi-property requests grouped by compatible property sets and
    merges successful results back into the rows before normalization.
    """
    normalized_devices = [dict(device) for device in devices]
    resource_ids: list[int | str] = [
        value
        for device in normalized_devices
        if (value := _device_id(device)) is not None
    ]
    if not resource_ids:
        return normalized_devices

    requests = _hydration_requests(normalized_devices, product_schemas or {})
    if diagnostics is not None:
        diagnostics.record_requests(requests)
    if not requests:
        return normalized_devices

    merged_values: dict[str, dict[str, Any]] = {}
    for properties, grouped_resource_ids in requests.items():
        try:
            response = await client.read_nodes_properties(
                house_id=house_id,
                node_kind="device",
                resource_ids=grouped_resource_ids,
                properties=list(properties),
            )
        except AuthenticationError:
            raise
        except Exception as err:
            _LOGGER.warning(
                "Failed to hydrate Yeelight Pro device properties group "
                "(resources=%s, properties=%s): %s",
                len(grouped_resource_ids),
                len(properties),
                safe_error_summary(err),
            )
            if diagnostics is not None:
                diagnostics.record_failure()
            continue
        parsed_values = _parse_multi_node_property_response(
            response if isinstance(response, Mapping) else {}
        )
        if diagnostics is not None:
            diagnostics.record_response(parsed_values)
        for device_id, values in parsed_values.items():
            merged_values.setdefault(device_id, {}).update(values)

    values_by_device = merged_values
    await _hydrate_indexed_subdevice_properties(
        client,
        house_id=house_id,
        devices=normalized_devices,
        values_by_device=values_by_device,
        diagnostics=diagnostics,
    )
    if diagnostics is not None:
        diagnostics.record_merge(values_by_device)
    if not values_by_device:
        return normalized_devices

    return [
        _merge_property_values(device, values_by_device.get(str(_device_id(device)), {}))
        for device in normalized_devices
    ]


def _hydration_requests(
    devices: Sequence[Mapping[str, Any]],
    product_schemas: Mapping[int, Mapping[str, Any]],
) -> dict[tuple[str, ...], list[int | str]]:
    """Return grouped read-side hydration requests by exact property set."""
    grouped: dict[tuple[str, ...], list[int | str]] = {}
    for device in devices:
        device_id = _device_id(device)
        if device_id is None:
            continue
        properties = _device_hydration_properties(device, product_schemas)
        if properties:
            grouped.setdefault(tuple(properties), []).append(device_id)
    return grouped


def _device_hydration_properties(
    device: Mapping[str, Any],
    product_schemas: Mapping[int, Mapping[str, Any]],
) -> list[str]:
    """Return a bounded property list for one device read request."""
    props: set[str] = set()
    existing_props = _existing_property_ids(device)
    props.update(existing_props)
    category = infer_iot_category(device)
    schema_props: set[str] = set()
    if schema := product_schemas.get(to_int(device.get("pid")) or -1):
        if not schema_conflicts_with_runtime_category(
            device,
            schema,
            runtime_category=category,
        ):
            schema_props = _schema_property_ids(schema)
            props.update(schema_props)
    catalog_props = set(product_hydration_properties(device.get("pid")))
    props.update(catalog_props)
    if category:
        props.update(_CATEGORY_EXTRA_PROPERTIES.get(category, ()))
    if not props or _needs_broad_property_discovery(
        device,
        inferred_category=category,
        existing_props=existing_props,
        schema_props=schema_props,
    ):
        props.update(DEFAULT_HYDRATION_PROPERTIES)
    return _ordered_properties(props)


def _ordered_properties(props: set[str]) -> list[str]:
    """Return stable reads without dropping documented product-only props."""
    ordered = [prop for prop in DEFAULT_HYDRATION_PROPERTIES if prop in props]
    ordered.extend(sorted(props - set(DEFAULT_HYDRATION_PROPERTIES)))
    return ordered


def _needs_broad_property_discovery(
    device: Mapping[str, Any],
    *,
    inferred_category: str | None,
    existing_props: set[str],
    schema_props: set[str],
) -> bool:
    """Return true when a broad cloud category needs read-side disambiguation."""
    if (existing_props | schema_props) - {"o"}:
        return False
    if inferred_category not in {None, "light", "relay_switch", "switch", "other"}:
        return False
    raw_category = to_str(device.get("category", device.get("type")))
    if raw_category is None:
        return True
    category = raw_category.strip().lower().replace("_", " ").replace("-", " ")
    return category in {"", "light", "relay switch", "relay_switch", "switch", "sensor"}


def _merge_property_values(
    device: Mapping[str, Any],
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge read values into a device row while preserving metadata."""
    if not values:
        return dict(device)

    merged = dict(device)
    existing = _property_list(merged.get("properties"))
    by_prop = {_property_id(item): dict(item) for item in existing if _property_id(item)}
    for prop, value in values.items():
        if value is None:
            continue
        item = by_prop.setdefault(prop, {"propId": prop})
        item["value"] = value
    if by_prop:
        merged["properties"] = list(by_prop.values())
    return merged


async def _hydrate_indexed_subdevice_properties(
    client: PropertyHydrationClient,
    *,
    house_id: int,
    devices: Sequence[Mapping[str, Any]],
    values_by_device: dict[str, dict[str, Any]],
    diagnostics: PropertyHydrationDiagnostics | None,
) -> None:
    """Fill missing ``N-prop`` values for indexed OpenAPI sub-devices."""
    for device in devices:
        device_id = _device_id(device)
        if device_id is None:
            continue
        device_key = str(device_id)
        indexed_requests = _indexed_subdevice_missing_properties(
            device,
            values_by_device.get(device_key, {}),
        )
        if not indexed_requests:
            continue
        merged_values = values_by_device.setdefault(device_key, {})
        for index, properties in indexed_requests.items():
            try:
                response = await client.read_node_properties(
                    house_id=house_id,
                    node_kind="device",
                    resource_id=device_id,
                    properties=properties,
                    index=index,
                )
            except AuthenticationError:
                raise
            except Exception as err:
                _LOGGER.warning(
                    "Failed to hydrate Yeelight Pro indexed sub-device properties "
                    "(resource=%s, index=%s, properties=%s): %s",
                    device_id,
                    index,
                    len(properties),
                    safe_error_summary(err),
                )
                if diagnostics is not None:
                    diagnostics.record_failure()
                continue
            values = _parse_indexed_node_property_response(
                response if isinstance(response, Mapping) else {},
                index=index,
            )
            if values:
                merged_values.update(values)
            elif not merged_values:
                values_by_device.pop(device_key, None)


def _indexed_subdevice_missing_properties(
    device: Mapping[str, Any],
    merged_values: Mapping[str, Any],
) -> dict[int, list[str]]:
    """Return per-index property ids still missing live values."""
    raw_params = device.get("params")
    params = raw_params if isinstance(raw_params, Mapping) else {}
    requests: dict[int, list[str]] = {}
    for subdevice in _property_list(device.get("subDeviceList")):
        index = to_int(subdevice.get("index"))
        if index is None:
            continue
        missing: list[str] = []
        for prop in _property_list(subdevice.get("properties")):
            prop_id = _property_id(prop)
            if prop_id is None:
                continue
            key = f"{index}-{prop_id}"
            if key in merged_values or key in params or _property_has_value(prop):
                continue
            missing.append(prop_id)
        if missing:
            requests[index] = _ordered_properties(set(missing))
    return requests


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


__all__ = ["DEFAULT_HYDRATION_PROPERTIES", "async_hydrate_device_properties"]
