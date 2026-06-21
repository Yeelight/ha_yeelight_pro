"""Strict user-control coverage helpers for private-house reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


STRICT_CONTROL_PLATFORMS = (
    "button",
    "climate",
    "cover",
    "fan",
    "light",
    "number",
    "select",
    "switch",
)
PRIMARY_CONTROL_PLATFORMS = ("button", "climate", "cover", "fan", "light", "switch")
EVENT_INPUT_CATEGORIES = frozenset({"knob_switch", "scene_panel"})
TOPOLOGY_CONTEXT_CATEGORIES = frozenset({"gateway"})
CONFIG_ONLY_CATEGORIES = frozenset({"other"})
CONFIG_ONLY_ROLES = frozenset({"config", "diagnostic"})
PRIMARY_CONTROL_ROLE = "primary_control_or_state"


def strict_control_counts(
    *,
    expected_platforms: Mapping[str, Any],
    actual_platforms: Mapping[str, Any],
    missing_platforms: Mapping[str, Any],
) -> dict[str, int]:
    """Return strict actionable-control counts from platform matrices."""
    return {
        "expected": _platform_total(expected_platforms, STRICT_CONTROL_PLATFORMS),
        "actual": _platform_total(actual_platforms, STRICT_CONTROL_PLATFORMS),
        "missing": _platform_total(missing_platforms, STRICT_CONTROL_PLATFORMS),
    }


def strict_control_platforms(platforms: Mapping[str, Any]) -> dict[str, int]:
    """Return strict control platform counts only."""
    return {
        platform: count
        for platform in STRICT_CONTROL_PLATFORMS
        if (count := _int_value(platforms.get(platform))) > 0
    }


def has_strict_control(platforms: Mapping[str, Any]) -> bool:
    """Return whether a platform matrix contains any actionable control."""
    return bool(strict_control_platforms(platforms))


def needs_missing_strict_control_review(
    *,
    category: Any,
    expected_roles: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
    expected_platforms: Mapping[str, Any],
    actual_platforms: Mapping[str, Any],
    source_evidence: Mapping[str, Any] | None = None,
    unprojected_writable_properties: Sequence[Any] | None = None,
    model_writable_properties_count: int,
) -> bool:
    """Return whether writable model evidence lacks a strict control entity."""
    if model_writable_properties_count <= 0:
        return False
    if unprojected_writable_properties == []:
        return False
    if has_strict_control(expected_platforms) or has_strict_control(actual_platforms):
        return False

    category_key = str(category or "").strip()
    if category_key in EVENT_INPUT_CATEGORIES | TOPOLOGY_CONTEXT_CATEGORIES:
        return False
    if _looks_like_event_input_subdevices(source_evidence or {}, expected_platforms):
        return False
    if category_key in CONFIG_ONLY_CATEGORIES and _roles_covered(
        expected_roles,
        actual_roles,
        allowed_roles=CONFIG_ONLY_ROLES,
    ):
        return False
    return True


def control_absence_reason(item: Mapping[str, Any]) -> str:
    """Return why the device has no strict actionable control entities."""
    actual_platforms = _mapping_value(item.get("actual_platforms"))
    expected_platforms = _mapping_value(item.get("expected_platforms"))
    if has_strict_control(actual_platforms) or has_strict_control(expected_platforms):
        return "strict_control_entities_present"

    category = str(item.get("category") or "")
    if category in TOPOLOGY_CONTEXT_CATEGORIES:
        return "gateway_or_topology_context_no_device_control"
    if category in EVENT_INPUT_CATEGORIES:
        return "event_input_device_events_are_not_controls"
    if _looks_like_event_input_subdevices(
        _mapping_value(item.get("source_evidence")),
        expected_platforms,
    ):
        return "event_input_subdevices_are_projected_as_events"
    if _int_value(item.get("model_writable_properties_count")) > 0:
        if _explicitly_no_unprojected_writable_properties(item):
            return "writable_properties_projected_as_state_or_event_entities"
        return "writable_model_properties_without_strict_control"
    if _looks_online_only_or_unknown_source(item):
        return "online_only_or_unknown_source_evidence"
    if _int_value(item.get("model_readable_properties_count")) > 0 or _sensor_platforms(item):
        return "read_only_state_or_event_device"
    return "no_supported_control_evidence"


def _roles_covered(
    expected_roles: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
    *,
    allowed_roles: frozenset[str],
) -> bool:
    expected = {
        str(role): _int_value(count)
        for role, count in expected_roles.items()
        if _int_value(count) > 0
    }
    if not expected or any(role not in allowed_roles for role in expected):
        return False
    return all(_int_value(actual_roles.get(role)) >= count for role, count in expected.items())


def _sensor_platforms(item: Mapping[str, Any]) -> bool:
    platforms = _mapping_value(item.get("expected_platforms")) or _mapping_value(
        item.get("actual_platforms")
    )
    return _int_value(platforms.get("binary_sensor")) > 0 or _int_value(
        platforms.get("sensor")
    ) > 0


def _explicitly_no_unprojected_writable_properties(item: Mapping[str, Any]) -> bool:
    """Return true when audit reverse lookup proved writable props are represented."""
    value = item.get("unprojected_writable_properties")
    return isinstance(value, list) and not value


def _looks_online_only_or_unknown_source(item: Mapping[str, Any]) -> bool:
    """Return true for devices whose only supported evidence is online/unknown."""
    evidence = _mapping_value(item.get("source_evidence"))
    if not bool(evidence.get("product_model_available", item.get("product_model", True))):
        return True
    raw_keys = {
        str(value)
        for value in evidence.get("raw_property_keys") or ()
        if value
    }
    return bool(raw_keys) and raw_keys <= {"o"} and _int_value(item.get("params_count")) <= 1


def _looks_like_event_input_subdevices(
    source_evidence: Mapping[str, Any],
    expected_platforms: Mapping[str, Any],
) -> bool:
    """Return true when writable subdevice channels are represented by events."""
    if _int_value(expected_platforms.get("event")) <= 0:
        return False
    if _int_value(source_evidence.get("subdevice_property_count")) <= 0:
        return False
    subdevice_keys = {
        str(value)
        for value in source_evidence.get("subdevice_property_keys") or ()
        if value
    }
    return any(key == "p" or key.endswith("-p") for key in subdevice_keys)


def _platform_total(platforms: Mapping[str, Any], names: tuple[str, ...]) -> int:
    return sum(_int_value(platforms.get(name)) for name in names)


def _mapping_value(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


__all__ = [
    "PRIMARY_CONTROL_PLATFORMS",
    "PRIMARY_CONTROL_ROLE",
    "STRICT_CONTROL_PLATFORMS",
    "control_absence_reason",
    "has_strict_control",
    "needs_missing_strict_control_review",
    "strict_control_counts",
    "strict_control_platforms",
]
