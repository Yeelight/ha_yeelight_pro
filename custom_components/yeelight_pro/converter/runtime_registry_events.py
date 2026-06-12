"""Registry-backed runtime event inference helpers."""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable, Mapping

from ..canonical.models import EventModel
from ..capabilities.models import IoTComponentSpec
from ..capabilities.registry import iot_registry

_COMPONENT_KEY_RE = re.compile(r"[\s_-]+")
_UNIQUE_CATEGORY_EVENT_FALLBACKS = frozenset({"contact_sensor"})


def registry_component_for_identity(
    values: tuple[Any, ...],
    *,
    category: Any = None,
    property_ids: Iterable[Any] = (),
) -> IoTComponentSpec | None:
    """Return an official component match from structured identity values."""
    registry = iot_registry()
    for value in values:
        spec = registry.component_map.get(component_key(value))
        if spec is not None:
            return spec
    return _unique_event_component_for_category(category, property_ids)


def registry_component_event_models(
    component: IoTComponentSpec | None,
) -> list[EventModel]:
    """Build canonical event models from official component-scoped events."""
    if component is None:
        return []
    return [
        EventModel(name=event_type, semantic=event_type, params=[])
        for event_type in component.events
    ]


def log_registry_event_inference(
    logger: logging.Logger,
    *,
    scope: str,
    payload: Mapping[str, Any],
    component_id: str,
    category: str | None,
    registry_component: IoTComponentSpec | None,
    events: list[EventModel],
) -> None:
    """Log registry-backed event inference without raw payload or user labels."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    if events:
        logger.debug(
            "Inferred %s events from IoT registry: device_id=%s component_id=%s "
            "category=%s registry_component_id=%s event_types=%s",
            scope,
            payload.get("device_id"),
            component_id,
            category,
            registry_component.component_id if registry_component else None,
            [event.semantic or event.name for event in events],
        )
        return
    if registry_component is None:
        reason = "missing_registry_component_identity"
    else:
        reason = "registry_component_without_events"
    logger.debug(
        "Skipping %s registry event inference: device_id=%s component_id=%s "
        "category=%s registry_component_id=%s reason=%s",
        scope,
        payload.get("device_id"),
        component_id,
        category,
        registry_component.component_id if registry_component else None,
        reason,
    )


def component_key(value: Any) -> str:
    """Normalize a registry component lookup key."""
    if value is None:
        return ""
    return _COMPONENT_KEY_RE.sub(" ", str(value).lower()).strip()


def _unique_event_component_for_category(
    category: Any,
    property_ids: Iterable[Any],
) -> IoTComponentSpec | None:
    """Use category as a final fallback only when it names one event component."""
    category_key = _category_key(category)
    if category_key not in _UNIQUE_CATEGORY_EVENT_FALLBACKS:
        return None
    prop_keys = {str(prop) for prop in property_ids if str(prop)}
    candidates = [
        component
        for component in iot_registry().components
        if component.category == category_key and component.events
    ]
    if prop_keys:
        candidates = [
            component
            for component in candidates
            if prop_keys & set(component.properties)
        ]
    return candidates[0] if len(candidates) == 1 else None


def _category_key(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


__all__ = [
    "component_key",
    "log_registry_event_inference",
    "registry_component_event_models",
    "registry_component_for_identity",
]
