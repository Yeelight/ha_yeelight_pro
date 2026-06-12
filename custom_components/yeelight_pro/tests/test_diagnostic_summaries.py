"""Diagnostic summary helper tests for Yeelight Pro."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.yeelight_pro.diagnostic_summaries import (
    entity_candidate_diagnostics,
    entity_import_filter_preview_diagnostics,
)


def test_entity_candidate_diagnostics_are_aggregate_only() -> None:
    """实体候选诊断只返回聚合计数，不返回 unique_id 或设备标识."""
    coordinator = SimpleNamespace(
        data={
            1: {
                "device_id": "device-secret-1",
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {"1-p": True, "2-sp": False},
            },
            2: {
                "device_id": "device-secret-2",
                "category": "other",
                "type": "vacuum",
                "online": False,
                "params": {"status": "idle", "battery": 80},
            },
        },
        scenes=[{"id": "scene-secret"}],
        groups=[],
        house_id=None,
        hide_unknown_entities=True,
    )

    summary = entity_candidate_diagnostics(coordinator)

    assert summary == {
        "total": 3,
        "platforms": {
            "button": 1,
            "switch": 2,
        },
        "device_platforms": {
            "switch": 2,
        },
        "sources": {
            "device": 2,
            "scene": 1,
        },
        "source_classes": {
            "device": 2,
            "topology": 1,
        },
        "duplicate_key_count": 0,
        "availability": {
            "available": 3,
            "unavailable": 0,
        },
    }
    assert "device-secret-1" not in str(summary)
    assert "scene-secret" not in str(summary)
    assert "yeelight_pro_device-secret-1_switch_1" not in str(summary)


def test_entity_import_filter_preview_counts_visible_device_entities_only() -> None:
    """实体过滤预览只影响设备候选，保留 scene/group/select 等拓扑候选。"""
    coordinator = SimpleNamespace(
        data={
            1: {
                "id": "dev-1",
                "device_id": "device-secret-1",
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {"1-p": True},
            },
            2: {
                "id": "dev-2",
                "device_id": "device-secret-2",
                "category": "other",
                "type": "vacuum",
                "online": True,
                "params": {"status": "idle", "battery": 80},
            },
        },
        scenes=[{"id": "scene-secret"}],
        groups=[{"id": "group-secret"}],
        house_id=12345,
        hide_unknown_entities=True,
    )

    summary = entity_import_filter_preview_diagnostics(
        coordinator,
        {
            "enabled": True,
            "exclude": {"devices": ["dev-2"]},
        },
    )

    assert summary == {
        "total": 8,
        "platforms": {
            "button": 1,
            "light": 1,
            "number": 2,
            "select": 3,
            "switch": 1,
        },
        "device_platforms": {
            "switch": 1,
        },
        "sources": {
            "device": 1,
            "group": 3,
            "house": 3,
            "scene": 1,
        },
        "source_classes": {
            "device": 1,
            "topology": 7,
        },
        "duplicate_key_count": 0,
        "availability": {
            "available": 8,
            "unavailable": 0,
        },
    }
    dumped = str(summary)
    for raw_marker in (
        "dev-1",
        "dev-2",
        "device-secret-1",
        "device-secret-2",
        "scene-secret",
        "group-secret",
        "12345",
    ):
        assert raw_marker not in dumped


def test_entity_candidate_diagnostics_count_duplicate_keys_safely() -> None:
    """重复候选只输出聚合数量，不泄露构成重复的原始标识。"""
    coordinator = SimpleNamespace(
        data={
            1: {
                "device_id": "duplicate-secret-device",
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {"1-p": True},
            },
            2: {
                "device_id": "duplicate-secret-device",
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {"1-p": False},
            },
        },
        scenes=[],
        groups=[],
        house_id=None,
        hide_unknown_entities=True,
    )

    summary = entity_candidate_diagnostics(coordinator)

    assert summary["total"] == 2
    assert summary["duplicate_key_count"] == 1
    assert summary["device_platforms"] == {
        "switch": 2,
    }
    assert summary["source_classes"] == {
        "device": 2,
    }
    dumped = str(summary)
    assert "duplicate-secret-device" not in dumped
    assert "yeelight_pro_duplicate-secret-device_switch_1" not in dumped
