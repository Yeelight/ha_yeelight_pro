"""DEBUG logging helpers for Yeelight Pro entity candidate projection."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
import logging
from typing import Any

_SENSITIVE_KEY_PARTS = frozenset({
    "access",
    "authorization",
    "bearer",
    "did",
    "ip",
    "mac",
    "password",
    "secret",
    "token",
})
_MAX_LOGGED_PROPS = 40


def log_device_candidate_filter_skip(
    logger: logging.Logger,
    device_payload: Mapping[str, Any],
) -> None:
    """Log why a runtime device produced no candidates because of the picker."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    logger.debug(
        "Skipping Yeelight Pro device entity candidates: device_id=%s "
        "category=%s type=%s reason=device_import_filter_excluded",
        _device_id(device_payload),
        device_payload.get("iot_category") or device_payload.get("category"),
        device_payload.get("type"),
    )


def log_device_candidate_summary(
    logger: logging.Logger,
    device_payload: Mapping[str, Any],
    candidates: Iterable[Any],
) -> None:
    """Log aggregate candidate domains and HA device-page sections."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    items = tuple(candidates)
    domain_counts = Counter(str(item.platform) for item in items)
    unavailable_counts = Counter(
        str(item.platform) for item in items if getattr(item, "available", True) is False
    )
    section_counts = Counter(_candidate_section(item) for item in items)
    prop_ids = _logged_prop_ids(device_payload)
    component_categories = _logged_component_categories(device_payload)
    reason = "projected_candidates" if items else "no_projected_candidates"
    logger.debug(
        "Projected Yeelight Pro device entity candidates: device_id=%s "
        "category=%s type=%s total=%s domains=%s sections=%s "
        "unavailable_domains=%s component_count=%s component_categories=%s "
        "prop_count=%s prop_ids=%s event_count=%s reason=%s",
        _device_id(device_payload),
        device_payload.get("iot_category") or device_payload.get("category"),
        device_payload.get("type"),
        len(items),
        dict(sorted(domain_counts.items())),
        dict(sorted(section_counts.items())),
        dict(sorted(unavailable_counts.items())),
        _component_count(device_payload),
        component_categories,
        len(prop_ids),
        _limit_log_values(prop_ids),
        _event_count(device_payload),
        reason,
    )


def _candidate_section(candidate: Any) -> str:
    """Return the HA device-page section represented by a candidate."""
    entity_category = getattr(candidate, "entity_category", None)
    if entity_category in {"config", "diagnostic"}:
        return str(entity_category)
    platform = str(getattr(candidate, "platform", ""))
    if platform in {"sensor", "binary_sensor"}:
        return "sensor"
    if platform == "event":
        return "event"
    return "control"


def _device_id(device_payload: Mapping[str, Any]) -> str | None:
    """Return a non-secret source id for diagnostics."""
    value = device_payload.get("device_id")
    return str(value) if value is not None else None


def _component_count(device_payload: Mapping[str, Any]) -> int:
    """Return the best non-sensitive component count available in the payload."""
    instance = device_payload.get("ha_device_instance")
    if isinstance(instance, Mapping):
        components = _rows(instance.get("components"))
        if components:
            return len(components)
    subdevices = _rows(device_payload.get("subDeviceList"))
    if subdevices:
        return len(subdevices)
    product_model = device_payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        return len(_rows(product_model.get("components")))
    return 0


def _logged_component_categories(device_payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return component category hints without logging user-visible names."""
    categories: set[str] = set()
    for component in _component_rows(device_payload):
        value = component.get("category")
        if isinstance(value, str) and value.strip():
            categories.add(value.strip())
    return tuple(sorted(categories))


def _logged_prop_ids(device_payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return safe property ids/keys that contributed to projection decisions."""
    props: set[str] = set()
    params = device_payload.get("params")
    if isinstance(params, Mapping):
        props.update(_safe_key(key) for key in params)
    for prop in _rows(device_payload.get("properties")):
        props.add(_safe_key(_property_id(prop)))
    for subdevice in _rows(device_payload.get("subDeviceList")):
        for prop in _rows(subdevice.get("properties")):
            props.add(_safe_key(_property_id(prop)))
    for component in _component_rows(device_payload):
        for prop in _rows(component.get("properties")):
            props.add(_safe_key(_property_id(prop)))
    props.discard("")
    return tuple(sorted(props))


def _component_rows(device_payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    """Return schema/runtime component rows used for aggregate logging."""
    rows: list[Mapping[str, Any]] = []
    instance = device_payload.get("ha_device_instance")
    if isinstance(instance, Mapping):
        rows.extend(_rows(instance.get("components")))
    product_model = device_payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        rows.extend(_rows(product_model.get("components")))
    return tuple(rows)


def _event_count(device_payload: Mapping[str, Any]) -> int:
    """Return documented event count without exposing event names or params."""
    total = len(_rows(device_payload.get("events")))
    for subdevice in _rows(device_payload.get("subDeviceList")):
        total += len(_rows(subdevice.get("events")))
    for component in _component_rows(device_payload):
        total += len(_rows(component.get("events")))
    return total


def _property_id(prop: Mapping[str, Any]) -> Any:
    """Return the documented property id field from one property row."""
    return prop.get("prop_id", prop.get("propId", prop.get("propName")))


def _safe_key(value: Any) -> str:
    """Return a key name only when it does not look like sensitive material."""
    if value is None:
        return ""
    text = str(value).strip()
    lowered = text.lower()
    if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
        return ""
    return text


def _rows(value: Any) -> list[Mapping[str, Any]]:
    """Return mapping rows from list-like schema fields."""
    return [item for item in value or [] if isinstance(item, Mapping)]


def _limit_log_values(values: tuple[str, ...]) -> tuple[str, ...]:
    """Bound high-cardinality DEBUG log fields while keeping counts exact."""
    if len(values) <= _MAX_LOGGED_PROPS:
        return values
    return (*values[:_MAX_LOGGED_PROPS], "...")
