"""Shared fixtures for entity-candidate tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from custom_components.yeelight_pro.identity import scoped_entity_unique_id


@dataclass
class EntityCandidateTestCoordinator:
    """Minimal coordinator shape required by entity candidate projection."""

    data: Mapping[Any, Mapping[str, Any]]
    scenes: list[dict[str, Any]] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    rooms: list[dict[str, Any]] = field(default_factory=list)
    areas: list[dict[str, Any]] = field(default_factory=list)
    houses: list[dict[str, Any]] = field(default_factory=list)
    house_id: int | None = None
    analytics_enabled: bool = False
    analytics_data: object | None = None
    hide_unknown_entities: bool = True
    options: dict[str, Any] = field(default_factory=dict)
    entry_data: dict[str, Any] = field(default_factory=dict)


def expected_unique_id(scope: str, *parts: Any) -> str:
    """Return expected scoped unique_id for topology/helper candidates."""
    return scoped_entity_unique_id(scope, *parts)


def light_payload() -> dict[str, Any]:
    """Build a minimal canonical light payload."""
    return {
        "device_id": "light-1",
        "category": "light",
        "type": "light",
        "online": True,
        "params": {"p": True, "l": 80},
        "ha_device_instance": {
            "device_id": "light-1",
            "name": "Light",
            "online": True,
            "device_info": {
                "identifiers": [["yeelight_pro", "light-1"]],
                "manufacturer": "Yeelight",
                "model": "light",
                "name": "Light",
            },
            "components": [
                {
                    "component_id": "main_light",
                    "category": "color temperature light",
                    "available": True,
                    "state": {"p": True, "l": 80},
                }
            ],
        },
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "model-light-1",
                "manufacturer": "Yeelight",
                "model": "light",
                "category": "light",
            },
            "components": [
                {
                    "component_id": "main_light",
                    "category": "color temperature light",
                    "events": [],
                }
            ],
        },
    }


_Coordinator = EntityCandidateTestCoordinator
_light_payload = light_payload
_uid = expected_unique_id

__all__ = [
    "EntityCandidateTestCoordinator",
    "_Coordinator",
    "_light_payload",
    "_uid",
    "expected_unique_id",
    "light_payload",
]
