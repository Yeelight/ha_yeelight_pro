"""Yeelight IoT registry integrity validation."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..const import PLATFORMS
from .data import NODE_TYPE_MAP
from .registry import YeelightIoTRegistry

_PLATFORM_NON_CATEGORIES = frozenset(
    {"event", "scene", "button", "select", "number", "vacuum", "text"}
)
_KNOWN_NODE_TYPES = frozenset({"room", "device", "area", "group", "house"})


def validate_iot_registry(registry: YeelightIoTRegistry) -> list[str]:
    """Return human-readable integrity issues for the static IoT registry."""
    errors: list[str] = []
    category_names = {category.category for category in registry.categories}
    component_aliases = {component.alias for component in registry.components}
    property_names = {prop.prop for prop in registry.properties}
    event_names = {event.normalized for event in registry.events}

    errors.extend(
        _duplicate_errors(
            "category",
            (category.category for category in registry.categories),
        )
    )
    errors.extend(
        _duplicate_errors(
            "category_id",
            (category.category_id for category in registry.categories),
        )
    )
    errors.extend(
        _duplicate_errors(
            "component_id",
            (component.component_id for component in registry.components),
        )
    )
    errors.extend(
        _duplicate_errors(
            "component_alias",
            (component.alias for component in registry.components),
        )
    )
    errors.extend(
        _duplicate_errors("property", (prop.prop for prop in registry.properties))
    )
    errors.extend(
        _duplicate_errors("event", (event.normalized for event in registry.events))
    )
    errors.extend(
        _duplicate_errors(
            "protocol_id",
            (protocol.protocol_id for protocol in registry.protocols),
        )
    )
    errors.extend(
        _duplicate_errors(
            "protocol_key",
            (protocol.key for protocol in registry.protocols),
        )
    )

    for category in registry.categories:
        if category.category in _PLATFORM_NON_CATEGORIES:
            errors.append(f"HA platform must not be an IoT category: {category.category}")
        if category.platform is not None and category.platform not in PLATFORMS:
            errors.append(
                f"category {category.category} maps to unknown HA platform "
                f"{category.platform}"
            )

    for platform in _PLATFORM_NON_CATEGORIES:
        if registry.is_iot_category(platform):
            errors.append(f"HA platform is incorrectly accepted as IoT category: {platform}")

    for component in registry.components:
        if component.category is not None and component.category not in category_names:
            errors.append(
                f"component {component.alias} references unknown category "
                f"{component.category}"
            )
        if (
            component.platform_hint is not None
            and component.platform_hint not in PLATFORMS
            and component.platform_hint != "button"
        ):
            errors.append(
                f"component {component.alias} has unknown platform hint "
                f"{component.platform_hint}"
            )
        for prop_name in component.properties:
            if prop_name not in property_names:
                errors.append(
                    f"component {component.alias} references unknown property "
                    f"{prop_name}"
                )
        for event_name in component.events:
            if event_name not in event_names:
                errors.append(
                    f"component {component.alias} references unknown event {event_name}"
                )

    for prop in registry.properties:
        if prop.capability is not None and prop.capability.prop != prop.prop:
            errors.append(
                f"property {prop.prop} capability prop mismatch: "
                f"{prop.capability.prop}"
            )
        if prop.unit is not None and prop.capability is not None:
            capability_unit = prop.capability.unit
            if capability_unit is not None and capability_unit != prop.unit:
                errors.append(
                    f"property {prop.prop} unit mismatch: {prop.unit} != "
                    f"{capability_unit}"
                )
        for component_alias in prop.components:
            if component_alias not in component_aliases:
                errors.append(
                    f"property {prop.prop} references unknown component "
                    f"{component_alias}"
                )

    event_aliases: dict[str, str] = {}
    for event in registry.events:
        for alias in (event.event_type, event.normalized, *event.aliases):
            normalized_alias = registry.normalize_event_type(alias)
            if normalized_alias is None:
                errors.append(f"event {event.normalized} has empty alias {alias!r}")
                continue
            previous = event_aliases.setdefault(normalized_alias, event.normalized)
            if previous != event.normalized:
                errors.append(
                    f"event alias {alias!r} maps to both {previous} and "
                    f"{event.normalized}"
                )
        for component_alias in event.components:
            if component_alias not in component_aliases:
                errors.append(
                    f"event {event.normalized} references unknown component "
                    f"{component_alias}"
                )

    for key, value in NODE_TYPE_MAP.items():
        if key not in _KNOWN_NODE_TYPES:
            errors.append(f"unknown nodeType key: {key}")
        if not isinstance(value, int) or value <= 0:
            errors.append(f"invalid nodeType value for {key}: {value}")

    return errors


def _duplicate_errors(label: str, values: Any) -> list[str]:
    """Return duplicate value errors for a registry field."""
    counts = Counter(values)
    return [
        f"duplicate {label}: {value}"
        for value, count in sorted(counts.items(), key=lambda item: str(item[0]))
        if count > 1
    ]
