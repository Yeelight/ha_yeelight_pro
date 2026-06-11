"""Runtime capability evidence helpers for Yeelight IoT devices."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..capabilities.registry import iot_registry, is_iot_category
from ..event_identity import SAFETY_EVENT_TYPES
from ..utils import to_str
from .device_classification_categories import CATEGORY_ALIASES
from .device_registry_classification import (
    normalized_prop_name,
    registry_category_from_property_keys,
)
from .device_runtime_constants import (
    EVENT_COMPONENT_CATEGORY_PRIORITY,
    FRESH_AIR_PROPS,
    LIGHT_SENSOR_CONFIG_PROPS,
    LIGHT_STATE_PROPS,
    NON_LIGHT_RUNTIME_CATEGORIES,
    RELAY_SWITCH_PROPS,
    RUNTIME_COMPONENT_CATEGORY_PRIORITY,
    SCHEMA_BROAD_CATEGORIES,
    TEMP_CONTROL_STRONG_PROPS,
)


def normalize_iot_category(value: Any) -> str | None:
    """Normalize Yeelight category aliases without treating names as categories."""
    text = to_str(value)
    if text is None:
        return None
    normalized = text.strip().lower().replace("_", " ").replace("-", " ")
    return CATEGORY_ALIASES.get(normalized, normalized.replace(" ", "_"))


def runtime_property_keys(payload: Mapping[str, Any]) -> set[str]:
    """Return runtime property ids from params/properties/subDeviceList only."""
    keys: set[str] = set()
    params = payload.get("params")
    if isinstance(params, Mapping):
        keys.update(normalized_prop_name(key) for key in params)
    for prop in _rows(payload.get("properties")):
        keys.add(normalized_prop_name(_property_id(prop)))
    for subdevice in _rows(payload.get("subDeviceList")):
        for prop in _rows(subdevice.get("properties")):
            keys.add(normalized_prop_name(_property_id(prop)))
    keys.discard("")
    return keys


def category_from_property_keys(
    keys: Iterable[str],
    *,
    current_category: Any = None,
) -> str | None:
    """Infer the most specific IoT category from documented property evidence."""
    props = {str(key) for key in keys if str(key)}
    category = normalize_iot_category(current_category)
    registry_category = registry_category_from_property_keys(
        props,
        current_category=category,
    )
    if (
        registry_category is not None
        and registry_category not in {"other", "temp_control"}
    ):
        return registry_category
    if (
        registry_category == "temp_control"
        and (category == "temp_control" or props & TEMP_CONTROL_STRONG_PROPS)
    ):
        return registry_category
    if category == "light_sensor" and props & {"luminance", "level", "mv"}:
        return "light_sensor"
    if category == "human_sensor" and props & {"mv", "luminance"}:
        return "human_sensor"
    if category == "contact_sensor" and props & {"dc", "alm"}:
        return "contact_sensor"
    if category == "curtain" and props & {"cp", "tp", "rd", "tra", "cra", "rs", "trs"}:
        return "curtain"
    if category in {"relay_switch", "switch"} and props & RELAY_SWITCH_PROPS:
        return "relay_switch"
    if category == "temp_control" and props & {
        "acp",
        "acm",
        "actt",
        "acct",
        "acf",
        "aco",
        "rfhp",
        "rfhct",
        "rfhtt",
        "tgt",
        "fa",
        "he",
        "bhm",
        "do",
        "ve",
        "t",
        "h",
    }:
        return "temp_control"

    if props & FRESH_AIR_PROPS:
        return "temp_control"
    if props & LIGHT_SENSOR_CONFIG_PROPS and props & {"luminance", "mv"}:
        return "light_sensor"
    if props & {"mv"}:
        return "human_sensor"
    if props & {"dc"}:
        return "contact_sensor"
    if props & {"cp", "tp", "rd", "tra", "cra"}:
        return "curtain"
    if props & {"acp", "acm", "actt", "acct", "acf", "aco", "rfhp", "rfhct", "rfhtt"}:
        return "temp_control"
    if props & {"tgt", "fa", "he", "bhm", "do", "ve"}:
        return "temp_control"
    if props & {"luminance", "level"} and not props & LIGHT_STATE_PROPS:
        return "light_sensor"
    if props & {"curp", "iec", "ap", "ae", "t", "h", "temp", "bl", "bc", "bcg"}:
        if not props & LIGHT_STATE_PROPS:
            return "other"
    if props & {"alm"}:
        return "contact_sensor"
    if registry_category is not None:
        return registry_category

    if category == "light" and props & {"p", "l", "ct", "c"}:
        return "light"
    return None


def runtime_component_categories(payload: Mapping[str, Any]) -> set[str]:
    """Return categories declared by runtime rows, excluding product schema."""
    categories: set[str] = set()
    for subdevice in _rows(payload.get("subDeviceList")):
        if category := normalize_iot_category(subdevice.get("category")):
            categories.add(category)
    instance = payload.get("ha_device_instance")
    if isinstance(instance, Mapping):
        for component in _rows(instance.get("components")):
            if category := normalize_iot_category(component.get("category")):
                categories.add(category)
    return categories


def category_from_event_capabilities(
    payload: Mapping[str, Any],
    *,
    current_category: Any = None,
) -> str | None:
    """Infer an IoT category from explicit event capability declarations."""
    event_types = _event_types(payload)
    if not event_types:
        return None

    category = normalize_iot_category(current_category)
    if set(SAFETY_EVENT_TYPES).issubset(event_types):
        return "other"

    categories = _categories_for_event_types(event_types)
    if not categories:
        return "other"
    if category in categories:
        return category
    for candidate in EVENT_COMPONENT_CATEGORY_PRIORITY:
        if candidate in categories and len(categories) == 1:
            return candidate
    return "other"


def infer_runtime_iot_category(payload: Mapping[str, Any]) -> str | None:
    """Infer category from runtime properties/components before schema fallback."""
    keys = runtime_property_keys(payload)
    if category := _category_from_runtime_components(payload, keys):
        return category
    if category := category_from_property_keys(
        keys,
        current_category=payload.get("iot_category")
        or payload.get("category")
        or payload.get("type"),
    ):
        return category
    if category := category_from_event_capabilities(
        payload,
        current_category=payload.get("iot_category")
        or payload.get("category")
        or payload.get("type"),
    ):
        return category
    return None


def schema_categories(schema: Mapping[str, Any]) -> set[str]:
    """Return normalized category labels declared by a product schema."""
    categories: set[str] = set()
    if category := normalize_iot_category(schema.get("category")):
        categories.add(category)
    for key in ("components", "customComponents"):
        for component in _rows(schema.get(key)):
            if category := normalize_iot_category(component.get("category")):
                categories.add(category)
    return categories


def schema_conflicts_with_runtime_category(
    payload: Mapping[str, Any],
    product_schema: Mapping[str, Any],
    *,
    runtime_category: str | None = None,
) -> bool:
    """Return true when a broad schema conflicts with runtime capabilities."""
    category = runtime_category or infer_runtime_iot_category(payload)
    if category not in NON_LIGHT_RUNTIME_CATEGORIES:
        return False
    if (
        category == "other"
        and not runtime_property_keys(payload)
        and not _runtime_events(payload)
    ):
        return False
    categories = schema_categories(product_schema)
    if not categories or category in categories:
        return False
    return bool(categories & SCHEMA_BROAD_CATEGORIES)


def state_blocks_light_projection(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Return true when scoped state proves this component is not a light."""
    keys = {normalized_prop_name(key) for key in state}
    declared_category = normalize_iot_category(
        device_payload.get("iot_category")
        or device_payload.get("category")
        or device_payload.get("type")
    )
    if declared_category in {"relay_switch", "switch"} and keys & RELAY_SWITCH_PROPS:
        return True
    if keys & LIGHT_STATE_PROPS:
        return False
    category = category_from_property_keys(
        keys,
        current_category=declared_category,
    )
    return category in NON_LIGHT_RUNTIME_CATEGORIES


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _category_from_runtime_components(
    payload: Mapping[str, Any],
    keys: set[str],
) -> str | None:
    """Return category declared by runtime component rows before property guesses."""
    categories = {
        category
        for category in runtime_component_categories(payload)
        if category and is_iot_category(category)
    }
    if not categories:
        return None
    for category in RUNTIME_COMPONENT_CATEGORY_PRIORITY:
        if category not in categories:
            continue
        if category == "light" and not keys & {"p", "l", "ct", "c"}:
            continue
        if category == "relay_switch" and not keys & RELAY_SWITCH_PROPS:
            continue
        return category
    return None


def _event_types(payload: Mapping[str, Any]) -> set[str]:
    events: set[str] = set()
    registry = iot_registry()
    for event in _event_rows(payload.get("events")):
        if event_type := _event_type(event, registry):
            events.add(event_type)
    for subdevice in _rows(payload.get("subDeviceList")):
        for event in _event_rows(subdevice.get("events")):
            if event_type := _event_type(event, registry):
                events.add(event_type)
    schema = payload.get("product_schema")
    if isinstance(schema, Mapping):
        for component in _schema_components(schema):
            for event in _event_rows(component.get("events")):
                if event_type := _event_type(event, registry):
                    events.add(event_type)
    product_model = payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        for component in _rows(product_model.get("components")):
            for event in _event_rows(component.get("events")):
                if event_type := _event_type(event, registry):
                    events.add(event_type)
    return events


def _runtime_events(payload: Mapping[str, Any]) -> set[str]:
    events: set[str] = set()
    registry = iot_registry()
    for event in _event_rows(payload.get("events")):
        if event_type := _event_type(event, registry):
            events.add(event_type)
    for subdevice in _rows(payload.get("subDeviceList")):
        for event in _event_rows(subdevice.get("events")):
            if event_type := _event_type(event, registry):
                events.add(event_type)
    return events


def _categories_for_event_types(event_types: set[str]) -> set[str]:
    registry = iot_registry()
    event_specs = {
        event.normalized: event
        for event in registry.events
        if event.normalized in event_types
    }
    categories: set[str] = set()
    for event in event_specs.values():
        for component_alias in event.components:
            if component := registry.component_map.get(_component_key(component_alias)):
                if component.category:
                    categories.add(component.category)
    categories.discard("")
    return categories


def _event_rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _event_type(event: Mapping[str, Any], registry: Any) -> str | None:
    event_id = event.get("event_id", event.get("eventId", event.get("id")))
    return (
        registry.normalize_event_type(event.get("semantic"))
        or registry.normalize_event_type(event.get("name"))
        or registry.normalize_event_type(event.get("desc"))
        or registry.normalize_event_type(event_id)
    )


def _schema_components(schema: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    components: list[Mapping[str, Any]] = []
    for key in ("components", "customComponents"):
        components.extend(_rows(schema.get(key)))
    return components


def _component_key(value: Any) -> str:
    text = to_str(value)
    if not text:
        return ""
    return " ".join(text.lower().replace("_", " ").replace("-", " ").split())


def _property_id(prop: Mapping[str, Any]) -> Any:
    return prop.get("prop_id", prop.get("propId", prop.get("propName")))


__all__ = [
    "EVENT_COMPONENT_CATEGORY_PRIORITY",
    "LIGHT_STATE_PROPS",
    "NON_LIGHT_RUNTIME_CATEGORIES",
    "RUNTIME_COMPONENT_CATEGORY_PRIORITY",
    "category_from_event_capabilities",
    "category_from_property_keys",
    "infer_runtime_iot_category",
    "normalize_iot_category",
    "runtime_property_keys",
    "schema_categories",
    "schema_conflicts_with_runtime_category",
    "state_blocks_light_projection",
]
