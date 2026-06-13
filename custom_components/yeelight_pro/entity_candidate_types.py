"""Shared entity-candidate types for Yeelight Pro lifecycle projection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

EntityKey = tuple[str, str]


class EntityCandidateCoordinator(Protocol):
    """候选生成需要的 coordinator 最小结构."""

    data: Mapping[Any, Mapping[str, Any]]
    scenes: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    rooms: list[dict[str, Any]]
    areas: list[dict[str, Any]]
    houses: list[dict[str, Any]]
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
    name: str | None = None
    icon: str | None = None
    entity_category: str | None = None
    suggested_object_id: str | None = None
    available: bool = True
    availability_reason: str | None = None

    @property
    def key(self) -> EntityKey:
        """Return the HA registry identity key."""
        return (self.platform, self.unique_id)


__all__ = [
    "EntityCandidate",
    "EntityCandidateCoordinator",
    "EntityKey",
]
