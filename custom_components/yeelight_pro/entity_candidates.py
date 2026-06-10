"""Projected Yeelight Pro entity candidates.

该模块集中生成 HA entity 候选，作为 projector 与实体生命周期之间的薄层。
第一阶段保持行为等价，只让 registry reconciliation 消费候选集合。
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .const import CONF_DEVICE_IMPORT_FILTER, DEFAULT_HIDE_UNKNOWN_ENTITIES, DOMAIN
from .device_filter import matches_device_import_filter
from .projector.binary_sensor import project_binary_sensors
from .projector.climate import project_climate
from .projector.cover import project_cover
from .projector.event import project_events
from .projector.fan import project_fans
from .projector.light import project_light
from .projector.lock import project_lock
from .projector.sensor import project_sensors
from .projector.switch import project_switches
from .projector.vacuum import project_vacuum


EntityKey = tuple[str, str]


class EntityCandidateCoordinator(Protocol):
    """候选生成需要的 coordinator 最小结构."""

    data: Mapping[Any, Mapping[str, Any]]
    scenes: list[dict[str, Any]]
    automations: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    house_id: int | None
    hide_unknown_entities: bool


@dataclass(frozen=True, slots=True)
class EntityCandidate:
    """Projected entity candidate before HA platform entity construction."""

    platform: str
    unique_id: str
    source: str
    device_id: str | None = None
    component_id: str | None = None
    available: bool = True
    availability_reason: str | None = None

    @property
    def key(self) -> EntityKey:
        """Return the HA registry identity key."""
        return (self.platform, self.unique_id)


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
            continue
        yield from iter_device_entity_candidates(
            device_payload,
            hide_unknown_entities=hide_unknown_entities,
        )
    yield from _iter_scene_candidates(coordinator.scenes)
    yield from _iter_automation_candidates(coordinator.automations)
    yield from _iter_group_candidates(coordinator.groups)
    yield from _iter_house_select_candidates(coordinator.house_id)


def iter_device_entity_candidates(
    device_payload: Mapping[str, Any],
    *,
    hide_unknown_entities: bool = DEFAULT_HIDE_UNKNOWN_ENTITIES,
) -> Iterator[EntityCandidate]:
    """Yield entity candidates projected from one runtime device payload."""
    device_id = _device_id(device_payload)

    light = project_light(device_payload, domain=DOMAIN)
    if light is not None:
        yield _candidate("light", light.unique_id, "device", device_id, light)

    for fan_projection in project_fans(device_payload, domain=DOMAIN):
        yield _candidate(
            "fan",
            fan_projection.unique_id,
            "device",
            device_id,
            fan_projection,
        )

    cover = project_cover(device_payload, domain=DOMAIN)
    if cover is not None:
        yield _candidate("cover", cover.unique_id, "device", device_id, cover)

    climate = project_climate(device_payload, domain=DOMAIN)
    if climate is not None:
        yield _candidate("climate", climate.unique_id, "device", device_id, climate)

    lock = project_lock(device_payload, domain=DOMAIN)
    if lock is not None:
        yield _candidate("lock", lock.unique_id, "device", device_id, lock)

    for switch_projection in project_switches(device_payload, domain=DOMAIN):
        yield _candidate(
            "switch",
            switch_projection.unique_id,
            "device",
            device_id,
            switch_projection,
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

    vacuum = project_vacuum(device_payload, domain=DOMAIN)
    if vacuum is not None:
        yield _candidate("vacuum", vacuum.unique_id, "device", device_id, vacuum)


def collect_entity_candidate_keys(
    coordinator: EntityCandidateCoordinator,
) -> set[EntityKey]:
    """Return all active HA registry keys from projected candidates."""
    return {candidate.key for candidate in iter_entity_candidates(coordinator)}


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
        available=available,
        availability_reason=None if available else "unavailable",
    )


def _iter_scene_candidates(scenes: list[dict[str, Any]]) -> Iterator[EntityCandidate]:
    """Yield candidates for Yeelight scenes."""
    for scene in scenes:
        scene_id = scene.get("id") or scene.get("sceneId")
        if not scene_id:
            continue
        unique_id = f"{DOMAIN}_scene_{scene_id}"
        yield EntityCandidate("button", unique_id, "scene", component_id=str(scene_id))
        yield EntityCandidate("scene", unique_id, "scene", component_id=str(scene_id))


def _iter_automation_candidates(
    automations: list[dict[str, Any]],
) -> Iterator[EntityCandidate]:
    """Yield candidates for Yeelight automations."""
    for automation in automations:
        auto_id = automation.get("id") or automation.get("automationId")
        if auto_id:
            yield EntityCandidate(
                "button",
                f"{DOMAIN}_automation_{auto_id}",
                "automation",
                component_id=str(auto_id),
            )


def _iter_group_candidates(groups: list[dict[str, Any]]) -> Iterator[EntityCandidate]:
    """Yield candidates for Yeelight group controls."""
    for group in groups:
        group_id = group.get("id") or group.get("groupId")
        if not group_id:
            continue
        yield EntityCandidate(
            "number",
            f"{DOMAIN}_group_{group_id}_brightness",
            "group",
            component_id=str(group_id),
        )
        yield EntityCandidate(
            "number",
            f"{DOMAIN}_group_{group_id}_color_temp",
            "group",
            component_id=str(group_id),
        )


def _iter_house_select_candidates(
    house_id: int | None,
) -> Iterator[EntityCandidate]:
    """Yield fixed house-level select candidates."""
    if not house_id:
        return
    for selector in ("room", "group", "scene"):
        yield EntityCandidate(
            "select",
            f"{DOMAIN}_{house_id}_select_{selector}",
            "house",
            component_id=selector,
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


def _device_id(device_payload: Mapping[str, Any]) -> str | None:
    """Return a stable source device id for diagnostics/debug consumers."""
    value = device_payload.get("device_id")
    return str(value) if value is not None else None


__all__ = [
    "EntityCandidate",
    "EntityCandidateCoordinator",
    "EntityKey",
    "collect_entity_candidate_keys",
    "iter_device_entity_candidates",
    "iter_entity_candidates",
]
