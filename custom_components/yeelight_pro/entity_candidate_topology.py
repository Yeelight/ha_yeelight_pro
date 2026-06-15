"""Topology and house-level entity candidates for Yeelight Pro."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from .device_display import suggested_entity_object_id
from .entity_candidate_types import EntityCandidate, EntityCandidateCoordinator
from .entity_category import ENTITY_CATEGORY_CONFIG, ENTITY_CATEGORY_DIAGNOSTIC
from .house_metadata import house_device_info
from .identity import coordinator_identity_scope, entity_unique_id
from .node_metadata import (
    NODE_LIGHT_KINDS,
    iter_topology_node_rows,
    node_kind_icon,
    node_light_unique_id,
    topology_node_id,
    topology_node_name,
)
from .scene_helpers import scene_row_id


def iter_topology_entity_candidates(
    coordinator: EntityCandidateCoordinator,
    *,
    analytics_enabled: bool,
) -> Iterator[EntityCandidate]:
    """Yield non-device candidates derived from scenes/topology/house helpers."""
    yield from _iter_scene_candidates(coordinator)
    yield from _iter_group_candidates(coordinator)
    yield from _iter_node_light_candidates(coordinator)
    yield from _iter_house_analytics_candidates(coordinator, analytics_enabled)
    yield from _iter_house_select_candidates(coordinator)


def _iter_scene_candidates(
    coordinator: EntityCandidateCoordinator,
) -> Iterator[EntityCandidate]:
    """Yield action candidates for Yeelight cloud scenes."""
    for scene in coordinator.scenes:
        scene_id = scene_row_id(scene)
        if not scene_id:
            continue
        yield EntityCandidate(
            "button",
            entity_unique_id(coordinator, "scene", scene_id),
            "scene",
            component_id=str(scene_id),
            name=_scene_name(scene, scene_id),
            icon="mdi:palette",
            entity_category=ENTITY_CATEGORY_CONFIG,
        )


def _iter_group_candidates(
    coordinator: EntityCandidateCoordinator,
) -> Iterator[EntityCandidate]:
    """生成 Yeelight 灯组控制候选。"""
    for group in coordinator.groups:
        group_id = group.get("id") or group.get("groupId")
        if not group_id:
            continue
        name = _group_name(group, group_id)
        yield EntityCandidate(
            "light",
            entity_unique_id(coordinator, "group", group_id, "light"),
            "group",
            component_id=str(group_id),
            name=name,
            icon="mdi:lightbulb-group",
        )
        yield EntityCandidate(
            "number",
            entity_unique_id(coordinator, "group", group_id, "brightness"),
            "group",
            component_id=str(group_id),
            name=f"{name} 亮度",
            icon="mdi:brightness-percent",
            entity_category=ENTITY_CATEGORY_CONFIG,
        )
        yield EntityCandidate(
            "number",
            entity_unique_id(coordinator, "group", group_id, "color_temp"),
            "group",
            component_id=str(group_id),
            name=f"{name} 色温",
            icon="mdi:thermometer",
            entity_category=ENTITY_CATEGORY_CONFIG,
        )


def _iter_node_light_candidates(
    coordinator: EntityCandidateCoordinator,
) -> Iterator[EntityCandidate]:
    """生成房间/区域/整屋总控 light 候选。"""
    scope = coordinator_identity_scope(coordinator)
    for node_kind in NODE_LIGHT_KINDS:
        for row in iter_topology_node_rows(coordinator, node_kind):
            node_id = topology_node_id(row, node_kind)
            if node_id is None:
                continue
            yield EntityCandidate(
                "light",
                node_light_unique_id(scope, node_kind, node_id),
                node_kind,
                component_id=str(node_id),
                name=topology_node_name(row, node_kind, node_id),
                icon=node_kind_icon(node_kind),
            )


def _iter_house_analytics_candidates(
    coordinator: EntityCandidateCoordinator,
    analytics_enabled: bool,
) -> Iterator[EntityCandidate]:
    """生成房屋级数据分析 diagnostic sensor 候选。"""
    house_id = coordinator.house_id
    if house_id is None or not analytics_enabled:
        return
    sensor_names = {
        "alarm_total": ("报警总数", "mdi:alarm-light"),
        "alarm_high_risk_count": ("高危设备数量", "mdi:alert-circle"),
        "energy_total": ("用电量", "mdi:lightning-bolt"),
        "user_action_count": ("用户操作次数", "mdi:gesture-tap-button"),
    }
    for key, (name, icon) in sensor_names.items():
        yield EntityCandidate(
            "sensor",
            entity_unique_id(coordinator, "analytics", key),
            "analytics",
            component_id=key,
            name=name,
            icon=icon,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            suggested_object_id=_analytics_suggested_object_id(
                coordinator,
                house_id,
                key,
                name,
            ),
        )


def _analytics_suggested_object_id(
    coordinator: EntityCandidateCoordinator,
    house_id: int,
    key: str,
    name: str,
) -> str | None:
    """Return the same house-level object-id seed used by analytics entities."""
    return suggested_entity_object_id(
        house_device_info(
            _HouseCandidateCoordinator(
                house_id,
                getattr(coordinator, "entry_data", None),
            )
        ),
        entity_name=name,
        fallback_id=f"house_{house_id}_analytics_{key}",
    )


class _HouseCandidateCoordinator:
    """Minimal coordinator shape for house-level suggested object ids."""

    def __init__(
        self,
        house_id: int,
        entry_data: Mapping[str, Any] | None = None,
    ) -> None:
        self.house_id = house_id
        self.entry_data = dict(entry_data or {})
        self.houses: list[dict[str, Any]] = []


def _iter_house_select_candidates(
    coordinator: EntityCandidateCoordinator,
) -> Iterator[EntityCandidate]:
    """生成固定的家庭级 select 候选。"""
    if coordinator.house_id is None:
        return
    selector_icons = {
        "room": "mdi:floor-plan",
        "group": "mdi:lightbulb-group",
        "scene": "mdi:palette",
    }
    for selector, icon in selector_icons.items():
        yield EntityCandidate(
            "select",
            entity_unique_id(coordinator, "select", selector),
            "house",
            component_id=selector,
            name=None,
            icon=icon,
            entity_category=ENTITY_CATEGORY_CONFIG,
        )


def _scene_name(scene: Mapping[str, Any], scene_id: str) -> str:
    """Return a user-facing scene action name."""
    for key in ("name", "sceneName", "scene_name"):
        value = scene.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"情景 {scene_id}"


def _group_name(group: Mapping[str, Any], group_id: Any) -> str:
    """Return a user-facing group name."""
    for key in ("name", "groupName", "group_name"):
        value = group.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"灯组 {group_id}"


__all__ = ["iter_topology_entity_candidates"]
