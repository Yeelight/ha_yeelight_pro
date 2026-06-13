"""Projected Yeelight Pro entity candidates.

该模块集中生成 HA entity 候选，作为 projector 与实体生命周期之间的薄层。
第一阶段保持行为等价，只让 registry reconciliation 消费候选集合。
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
import logging
from typing import Any

from .const import CONF_DEVICE_IMPORT_FILTER, DEFAULT_HIDE_UNKNOWN_ENTITIES, DOMAIN
from .device_filter import matches_device_import_filter
from .device_display import suggested_entity_object_id
from .entity_candidate_logging import (
    log_device_candidate_filter_skip,
    log_device_candidate_summary,
)
from .entity_candidate_topology import iter_topology_entity_candidates
from .entity_candidate_types import (
    EntityCandidate,
    EntityCandidateCoordinator,
    EntityKey,
)
from .entity_category import ENTITY_CATEGORY_CONFIG, ENTITY_CATEGORY_DIAGNOSTIC
from .projector.binary_sensor import project_binary_sensors
from .projector.climate import project_climates
from .projector.cover import project_covers
from .projector.event import project_events
from .projector.fan import project_fans
from .projector.light import project_lights
from .projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)
from .projector.sensor import project_sensors
from .projector.switch import project_switches

_LOGGER = logging.getLogger(__name__)


def iter_entity_candidates(
    coordinator: EntityCandidateCoordinator,
) -> Iterator[EntityCandidate]:
    """Yield all entity candidates for the current Yeelight topology."""
    hide_unknown_entities = bool(
        getattr(coordinator, "hide_unknown_entities", DEFAULT_HIDE_UNKNOWN_ENTITIES)
    )
    device_import_filter = _device_import_filter(coordinator)
    for device_payload in coordinator.data.values():
        if not matches_device_import_filter(device_payload, device_import_filter):
            log_device_candidate_filter_skip(_LOGGER, device_payload)
            continue
        device_candidates = list(iter_device_entity_candidates(
            device_payload,
            hide_unknown_entities=hide_unknown_entities,
        ))
        log_device_candidate_summary(_LOGGER, device_payload, device_candidates)
        yield from device_candidates
    yield from iter_topology_entity_candidates(
        coordinator,
        analytics_enabled=bool(getattr(coordinator, "analytics_enabled", False)),
    )


def iter_device_entity_candidates(
    device_payload: Mapping[str, Any],
    *,
    hide_unknown_entities: bool = DEFAULT_HIDE_UNKNOWN_ENTITIES,
) -> Iterator[EntityCandidate]:
    """Yield entity candidates projected from one runtime device payload."""
    device_id = _device_id(device_payload)

    for light in project_lights(device_payload, domain=DOMAIN):
        yield _candidate("light", light.unique_id, "device", device_id, light)

    for fan_projection in project_fans(device_payload, domain=DOMAIN):
        yield _candidate("fan", fan_projection.unique_id, "device", device_id, fan_projection)

    for cover_projection in project_covers(device_payload, domain=DOMAIN):
        yield _candidate("cover", cover_projection.unique_id, "device", device_id, cover_projection)

    for climate_projection in project_climates(device_payload, domain=DOMAIN):
        yield _candidate(
            "climate",
            climate_projection.unique_id,
            "device",
            device_id,
            climate_projection,
        )

    for switch_projection in project_switches(device_payload, domain=DOMAIN):
        yield _candidate(
            "switch",
            switch_projection.unique_id,
            "device",
            device_id,
            switch_projection,
        )

    for switch_control in project_switch_controls(device_payload, domain=DOMAIN):
        yield _candidate(
            "switch",
            switch_control.unique_id,
            "device",
            device_id,
            switch_control,
        )

    for number_projection in project_number_controls(device_payload, domain=DOMAIN):
        yield _candidate(
            "number",
            number_projection.unique_id,
            "device",
            device_id,
            number_projection,
        )

    for select_projection in project_select_controls(device_payload, domain=DOMAIN):
        yield _candidate(
            "select",
            select_projection.unique_id,
            "device",
            device_id,
            select_projection,
        )

    for sensor_projection in project_sensors(
        device_payload,
        domain=DOMAIN,
        hide_unknown_entities=hide_unknown_entities,
    ):
        yield _candidate(
            "sensor",
            sensor_projection.unique_id,
            "device",
            device_id,
            sensor_projection,
        )

    for binary_sensor_projection in project_binary_sensors(device_payload, domain=DOMAIN):
        yield _candidate(
            "binary_sensor",
            binary_sensor_projection.unique_id,
            "device",
            device_id,
            binary_sensor_projection,
        )

    for event_projection in project_events(device_payload, domain=DOMAIN):
        yield _candidate(
            "event",
            event_projection.unique_id,
            "device",
            device_id,
            event_projection,
        )


def collect_entity_candidate_keys(
    coordinator: EntityCandidateCoordinator,
) -> set[EntityKey]:
    """Return all active HA registry keys from projected candidates."""
    return {candidate.key for candidate in iter_entity_candidates(coordinator)}


def collect_entity_candidates(
    coordinator: EntityCandidateCoordinator,
) -> dict[EntityKey, EntityCandidate]:
    """Return active HA registry candidates keyed by domain and unique id."""
    return {candidate.key: candidate for candidate in iter_entity_candidates(coordinator)}


def _candidate(
    platform: str,
    unique_id: str,
    source: str,
    device_id: str | None,
    projection: Any,
) -> EntityCandidate:
    """Build a candidate from an existing projector projection."""
    available = bool(getattr(projection, "available", True))
    return EntityCandidate(
        platform=platform,
        unique_id=unique_id,
        source=source,
        device_id=device_id,
        component_id=_projection_component_id(projection),
        name=_projection_name(projection),
        icon=_projection_icon(projection),
        entity_category=_projection_entity_category(projection),
        suggested_object_id=_suggested_projection_object_id(
            projection,
            fallback_id=device_id,
        ),
        available=available,
        availability_reason=None if available else "unavailable",
    )


def _device_import_filter(
    coordinator: EntityCandidateCoordinator,
) -> Mapping[str, Any] | None:
    """Return the stored device import filter for lifecycle candidates."""
    options = getattr(coordinator, "options", None)
    if not isinstance(options, Mapping):
        return None
    filter_config = options.get(CONF_DEVICE_IMPORT_FILTER)
    return filter_config if isinstance(filter_config, Mapping) else None


def _projection_component_id(projection: Any) -> str | None:
    """Return component_id from projector projections when available."""
    component_id = getattr(projection, "component_id", None)
    return component_id if isinstance(component_id, str) and component_id else None


def _projection_name(projection: Any) -> str | None:
    """Return a registry-safe projected entity name."""
    name = getattr(projection, "name", None)
    return name if isinstance(name, str) and name.strip() else None


def _projection_icon(projection: Any) -> str | None:
    """Return a registry-safe projected entity icon."""
    icon = getattr(projection, "icon", None)
    return icon if isinstance(icon, str) and icon.strip() else None


def _projection_entity_category(projection: Any) -> str | None:
    """Return an internal entity category from projector projections."""
    category = getattr(projection, "entity_category", None)
    return category if category in {ENTITY_CATEGORY_CONFIG, ENTITY_CATEGORY_DIAGNOSTIC} else None


def _suggested_projection_object_id(
    projection: Any,
    *,
    fallback_id: str | None,
) -> str | None:
    """Return HA object-id seed matching the runtime entity implementation."""
    device_info = getattr(projection, "device_info", None)
    if isinstance(device_info, dict):
        return suggested_entity_object_id(
            device_info,
            entity_name=_projection_name(projection),
            fallback_id=fallback_id,
        )
    return None


def _device_id(device_payload: Mapping[str, Any]) -> str | None:
    """Return a stable source device id for diagnostics/debug consumers."""
    value = device_payload.get("device_id")
    return str(value) if value is not None else None


__all__ = [
    "EntityCandidate",
    "EntityCandidateCoordinator",
    "EntityKey",
    "collect_entity_candidates",
    "collect_entity_candidate_keys",
    "iter_device_entity_candidates",
    "iter_entity_candidates",
]
