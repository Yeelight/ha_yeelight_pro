"""Tests for Yeelight Pro entity-registry reconciliation helpers."""
from __future__ import annotations

from types import SimpleNamespace

from custom_components.yeelight_pro.entity_lifecycle import (
    collect_active_entity_keys,
    collect_active_entity_unique_ids,
    entity_registry_reconcile_diagnostics,
)

from .entity_lifecycle_helpers import lifecycle_coordinator


def test_collect_active_entity_keys_keeps_scene_button_and_scene_separate() -> None:
    """Scene buttons and scene entities share ids but are different HA entities."""
    coordinator = SimpleNamespace(
        data={},
        scenes=[{"id": "scene_1"}],
        automations=[{"id": "auto_1"}],
        groups=[{"id": "group_1"}],
        house_id=12345,
    )

    keys = collect_active_entity_keys(coordinator)

    assert ("button", "yeelight_pro_scene_scene_1") in keys
    assert ("scene", "yeelight_pro_scene_scene_1") in keys
    assert ("button", "yeelight_pro_automation_auto_1") in keys
    assert ("number", "yeelight_pro_group_group_1_brightness") in keys
    assert ("number", "yeelight_pro_group_group_1_color_temp") in keys
    assert ("select", "yeelight_pro_12345_select_room") in keys
    assert ("select", "yeelight_pro_12345_select_group") in keys
    assert ("select", "yeelight_pro_12345_select_scene") in keys
    assert len(keys) == 8


def test_collect_active_entity_keys_includes_experimental_vacuum() -> None:
    """实验 vacuum 平台也必须参与生命周期 active key 计算."""
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

    assert ("vacuum", "yeelight_pro_88_vacuum") in keys


def test_collect_active_entity_unique_ids_preserves_legacy_unique_id_view() -> None:
    """The compatibility helper still exposes the unique-id-only set."""
    coordinator = SimpleNamespace(
        data={},
        scenes=[{"id": "scene_1"}],
        automations=[],
        groups=[],
        house_id=None,
    )

    unique_ids = collect_active_entity_unique_ids(coordinator)

    assert unique_ids == {"yeelight_pro_scene_scene_1"}


def test_entity_registry_reconcile_diagnostics_ignores_foreign_summary() -> None:
    """Only lifecycle-owned summary objects may enter diagnostics."""
    coordinator = SimpleNamespace(
        _yeelight_pro_last_entity_registry_reconcile_summary=SimpleNamespace(
            as_diagnostics=lambda: {"unique_id": "yeelight_pro_scene_secret"}
        )
    )

    assert entity_registry_reconcile_diagnostics(coordinator) is None
