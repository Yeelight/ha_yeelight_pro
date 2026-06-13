"""Tests for Yeelight Pro entity-registry reconciliation helpers."""
from __future__ import annotations

from types import SimpleNamespace

from custom_components.yeelight_pro.entity_lifecycle import (
    collect_active_entity_keys,
    collect_active_entity_unique_ids,
    entity_registry_reconcile_diagnostics,
)
from custom_components.yeelight_pro.identity import entry_identity_scope, scoped_entity_unique_id

from .entity_lifecycle_helpers import lifecycle_coordinator


def test_collect_active_entity_keys_projects_cloud_scenes_as_buttons_only() -> None:
    """云端情景只作为 button active key，旧 scene 实体应进入 stale 审计."""
    coordinator = SimpleNamespace(
        data={},
        scenes=[{"id": "scene_1"}],
        groups=[{"id": "group_1"}],
        house_id=12345,
    )

    keys = collect_active_entity_keys(coordinator)

    scope = entry_identity_scope({}, 12345)
    assert ("button", scoped_entity_unique_id(scope, "scene", "scene_1")) in keys
    assert ("light", scoped_entity_unique_id(scope, "group", "group_1", "light")) in keys
    assert ("number", scoped_entity_unique_id(scope, "group", "group_1", "brightness")) in keys
    assert ("number", scoped_entity_unique_id(scope, "group", "group_1", "color_temp")) in keys
    assert ("select", scoped_entity_unique_id(scope, "select", "room")) in keys
    assert ("select", scoped_entity_unique_id(scope, "select", "group")) in keys
    assert ("select", scoped_entity_unique_id(scope, "select", "scene")) in keys
    assert len(keys) == 7


def test_collect_active_entity_keys_excludes_unsupported_vacuum_payload() -> None:
    """无易来文档支撑的 vacuum-like payload 不能进入 active key。"""
    coordinator = lifecycle_coordinator(
        data={
            88: {
                "device_id": 88,
                "category": "other",
                "type": "vacuum",
                "online": True,
                "params": {"status": "cleaning", "battery": 80},
            }
        }
    )

    keys = collect_active_entity_keys(coordinator)

    assert keys == set()


def test_collect_active_entity_unique_ids_preserves_legacy_unique_id_view() -> None:
    """The compatibility helper still exposes the unique-id-only set."""
    coordinator = SimpleNamespace(
        data={},
        scenes=[{"id": "scene_1"}],
        groups=[],
        house_id=None,
    )

    scope = entry_identity_scope({}, 0)
    unique_ids = collect_active_entity_unique_ids(coordinator)

    assert unique_ids == {scoped_entity_unique_id(scope, "scene", "scene_1")}


def test_entity_registry_reconcile_diagnostics_ignores_foreign_summary() -> None:
    """Only lifecycle-owned summary objects may enter diagnostics."""
    coordinator = SimpleNamespace(
        _yeelight_pro_last_entity_registry_reconcile_summary=SimpleNamespace(
            as_diagnostics=lambda: {"unique_id": "yeelight_pro_scene_secret"}
        )
    )

    assert entity_registry_reconcile_diagnostics(coordinator) is None
