"""Hydrate runtime device rows with documented Yeelight property reads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import logging
from typing import Any, Protocol

from ..utils import to_int, to_str
from .device_classification import infer_iot_category
from .exceptions import AuthenticationError, safe_error_summary

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


async def async_hydrate_device_properties(
    client: PropertyHydrationClient,
    *,
    house_id: int,
    devices: Sequence[Mapping[str, Any]],
    product_schemas: Mapping[int, Mapping[str, Any]] | None = None,
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
            continue
        for device_id, values in _parse_multi_node_property_response(
            response if isinstance(response, Mapping) else {}
        ).items():
            merged_values.setdefault(device_id, {}).update(values)

    values_by_device = merged_values
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
        if not _schema_conflicts_with_runtime_category(category, schema):
            schema_props = _schema_property_ids(schema)
            props.update(schema_props)
    if category:
        props.update(_CATEGORY_EXTRA_PROPERTIES.get(category, ()))
    name_props = _name_hint_properties(device)
    props.update(name_props)
    if not props or _needs_broad_property_discovery(
        device,
        inferred_category=category,
        existing_props=existing_props,
        schema_props=schema_props,
        name_props=name_props,
    ):
        props.update(DEFAULT_HYDRATION_PROPERTIES)
    return [prop for prop in DEFAULT_HYDRATION_PROPERTIES if prop in props]


def _needs_broad_property_discovery(
    device: Mapping[str, Any],
    *,
    inferred_category: str | None,
    existing_props: set[str],
    schema_props: set[str],
    name_props: set[str],
) -> bool:
    """Return true when a broad cloud category needs read-side disambiguation."""
    if (existing_props | schema_props | name_props) - {"o"}:
        return False
    if inferred_category not in {None, "light", "relay_switch", "switch", "sensor", "other"}:
        return False
    raw_category = to_str(device.get("category", device.get("type")))
    if raw_category is None:
        return True
    category = raw_category.strip().lower().replace("_", " ").replace("-", " ")
    return category in {"", "light", "relay switch", "relay_switch", "switch", "sensor"}


def _schema_conflicts_with_runtime_category(
    category: str | None,
    schema: Mapping[str, Any],
) -> bool:
    """Return true when a broad schema should not drive property reads."""
    if category not in {"curtain", "temp_control", "scene_panel", "knob_switch"}:
        return False
    schema_categories = _schema_categories(schema)
    if not schema_categories or category in schema_categories:
        return False
    return bool(schema_categories & {"relay_switch", "switch", "light", "other"})


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


def _parse_multi_node_property_response(response: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Parse documented 3.2.7 response variants into values by resource id."""
    raw_data = response.get("data")
    if not isinstance(raw_data, Mapping):
        return {}

    parsed: dict[str, dict[str, Any]] = {}
    for resource_id, result in raw_data.items():
        if not isinstance(result, Mapping):
            continue
        code = to_str(result.get("code"))
        if code not in {None, "", "200"}:
            continue
        values = _property_values(result.get("data"))
        if values:
            parsed[str(resource_id)] = values
    return parsed


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


def _schema_categories(schema: Mapping[str, Any]) -> set[str]:
    """Return category labels declared by a product schema."""
    categories = {
        str(category)
        for category in (schema.get("category"),)
        if category is not None and str(category)
    }
    for key in ("components", "customComponents"):
        categories.update(
            str(component["category"])
            for component in _property_list(schema.get(key))
            if component.get("category") is not None and str(component.get("category"))
        )
    return categories


def _name_hint_properties(device: Mapping[str, Any]) -> set[str]:
    """Return read targets implied by user-facing product names."""
    name = " ".join(
        str(value)
        for key in ("name", "deviceName", "device_name", "n", "modelName", "model_name")
        if (value := device.get(key)) is not None
    ).lower()
    props: set[str] = set()
    if any(token in name for token in ("温湿度", "温度", "湿度", "temperature", "humidity")):
        props.update({"t", "temp", "h", "bl", "bc", "bcg", "o"})
    if any(token in name for token in ("门磁", "门窗", "contact")):
        props.update({"dc", "alm", "bl", "bc", "bcg", "o"})
    if any(token in name for token in ("人体", "人感", "存在", "motion", "presence")):
        props.update({"mv", "alm", "luminance", "bl", "bc", "bcg", "o"})
    if any(token in name for token in ("照度", "光照", "illuminance")):
        props.update({"luminance", "level", "bl", "bc", "bcg", "o"})
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
