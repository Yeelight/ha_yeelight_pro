"""Private-house coverage aggregate classification tests."""

from __future__ import annotations

from scripts.private_house_audit.classification import (
    ACTION_INVESTIGATE_SOURCE_DATA,
    ACTION_NO_CODE_CHANGE,
    ACTION_REGISTRY_REFRESH,
    ACTION_SYNC_RUNTIME,
    STATUS_REGISTRY_STALE,
    STATUS_RUNTIME_DRIFT,
    classify_report,
    markdown_report,
)

def test_classify_report_returns_action_counts() -> None:
    """整屋分类应给出可汇总的状态和行动计数."""
    report = {
        "devices": [
            {"name": "ok", "actual_total": 2, "expected_total": 2},
            {"name": "stale", "missing_total": 1, "missing_platforms": {"event": 1}},
            {
                "name": "limited",
                "actual_total": 1,
                "expected_total": 1,
                "params_count": 1,
                "low_coverage_reasons": ["low_runtime_property_evidence"],
            },
        ]
    }

    result = classify_report(report)

    assert result["summary"]["device_count"] == 3
    assert result["summary"]["actions"] == {
        ACTION_INVESTIGATE_SOURCE_DATA: 1,
        ACTION_NO_CODE_CHANGE: 1,
        ACTION_REGISTRY_REFRESH: 1,
    }


def test_classify_report_uses_install_runtime_status_for_missing_entities() -> None:
    """整屋报告应把安装态漂移作为 registry 缺失的前置结论。"""
    report = {
        "install_runtime": {
            "matched_source": False,
            "changed_files": 2,
            "changed_samples": ["dynamic_entities.py"],
        },
        "devices": [
            {
                "name": "四键",
                "missing_total": 3,
                "missing_platforms": {"event": 3},
            }
        ],
    }

    result = classify_report(report)

    assert result["summary"]["statuses"] == {STATUS_RUNTIME_DRIFT: 1}
    assert result["summary"]["actions"] == {ACTION_SYNC_RUNTIME: 1}
    assert result["summary"]["install_runtime"] == {
        "matched_source": False,
        "missing_files": 0,
        "extra_files": 0,
        "changed_files": 2,
        "missing_samples": [],
        "extra_samples": [],
        "changed_samples": ["dynamic_entities.py"],
    }
    assert result["devices"][0]["conclusion"]["status"] == STATUS_RUNTIME_DRIFT


def test_classify_report_preserves_topology_entity_coverage() -> None:
    """分类结果应保留房间/灯组/整屋/情景等拓扑实体覆盖结论."""
    report = {
        "summary": {
            "expected_topology_entities": 3,
            "actual_topology_entities": 2,
            "missing_topology_entities": 1,
            "topology_missing_platforms": {"button": 1},
        },
        "topology_entities": [
            {
                "source": "scene",
                "actual_total": 0,
                "expected_total": 1,
                "missing_total": 1,
                "expected_platforms": {"button": 1},
                "missing_platforms": {"button": 1},
                "expected_roles": {"config": 1},
                "missing_roles": {"config": 1},
                "expected_samples": [
                    {
                        "platform": "button",
                        "name": "回家",
                        "component_id": "scene-1",
                        "entity_category": "config",
                        "role": "config",
                    }
                ],
                "missing_samples": [
                    {
                        "platform": "button",
                        "name": "回家",
                        "component_id": "scene-1",
                        "entity_category": "config",
                        "role": "config",
                    }
                ],
            }
        ],
    }

    result = classify_report(report)

    assert result["summary"]["topology_count"] == 1
    assert result["summary"]["topology_actions"] == {
        ACTION_REGISTRY_REFRESH: 1,
    }
    assert result["summary"]["audit"]["missing_topology_entities"] == 1
    assert result["devices"] == []
    assert result["topology_entities"][0]["name"] == "topology:scene"
    assert result["topology_entities"][0]["conclusion"]["status"] == STATUS_REGISTRY_STALE
    assert result["topology_entities"][0]["missing_samples"][0]["platform"] == "button"


def test_classify_report_preserves_missing_entity_samples() -> None:
    """registry stale 设备应保留缺失实体样本，便于逐设备排查."""
    report = {
        "devices": [
            {
                "name": "四键",
                "category": "scene_panel",
                "missing_total": 1,
                "missing_platforms": {"event": 1},
                "missing_samples": [
                    {
                        "platform": "event",
                        "name": "按键一事件",
                        "component_id": "scene_panel_1",
                        "entity_category": "primary",
                        "role": "event",
                    }
                ],
            }
        ]
    }

    result = classify_report(report)

    assert result["devices"][0]["missing_samples"] == [
        {
            "platform": "event",
            "name": "按键一事件",
            "component_id": "scene_panel_1",
            "entity_category": "primary",
            "role": "event",
        }
    ]


def test_classify_report_preserves_expected_entity_samples() -> None:
    """分类 JSON 应保留预期实体样本，支撑逐设备完整性核查."""
    report = {
        "devices": [
            {
                "name": "四键",
                "category": "scene_panel",
                "actual_total": 1,
                "expected_total": 2,
                "expected_samples": [
                    {
                        "platform": "sensor",
                        "name": "在线状态",
                        "component_id": "online_status",
                        "entity_category": "diagnostic",
                        "role": "diagnostic",
                    },
                    {
                        "platform": "event",
                        "name": "按键一事件",
                        "component_id": "scene_panel_1",
                        "entity_category": "primary",
                        "role": "event",
                    },
                ],
            }
        ]
    }

    result = classify_report(report)

    assert result["devices"][0]["expected_samples"] == [
        {
            "platform": "sensor",
            "name": "在线状态",
            "component_id": "online_status",
            "entity_category": "diagnostic",
            "role": "diagnostic",
        },
        {
            "platform": "event",
            "name": "按键一事件",
            "component_id": "scene_panel_1",
            "entity_category": "primary",
            "role": "event",
        },
    ]


def test_classify_report_preserves_role_and_platform_matrices() -> None:
    """分类 JSON 应保留逐设备角色/平台矩阵，便于覆盖性审计."""
    report = {
        "devices": [
            {
                "name": "四键",
                "category": "scene_panel",
                "actual_total": 2,
                "expected_total": 5,
                "missing_total": 3,
                "extra_total": 1,
                "expected_roles": {"diagnostic": 1, "event": 4},
                "actual_roles": {"diagnostic": 1, "event": 1},
                "missing_roles": {"event": 3},
                "expected_platforms": {"event": 4, "sensor": 1},
                "actual_platforms": {"event": 1, "sensor": 1},
                "missing_platforms": {"event": 3},
                "source_evidence": {
                    "raw_property_count": 1,
                    "raw_property_keys": ["o"],
                    "subdevice_count": 0,
                    "subdevice_property_count": 0,
                    "product_model_available": True,
                },
            }
        ]
    }

    result = classify_report(report)
    device = result["devices"][0]

    assert device["extra_total"] == 1
    assert device["source_evidence"]["raw_property_keys"] == ["o"]
    assert device["expected_roles"] == {"diagnostic": 1, "event": 4}
    assert device["actual_roles"] == {"diagnostic": 1, "event": 1}
    assert device["expected_platforms"] == {"event": 4, "sensor": 1}
    assert device["actual_platforms"] == {"event": 1, "sensor": 1}
    assert device["strict_control"] == {
        "expected": 0,
        "actual": 0,
        "missing": 0,
        "absence_reason": "event_input_device_events_are_not_controls",
    }
    assert device["coverage_view"] == {
        "control": {
            "actual": 0,
            "expected": 0,
            "missing": 0,
            "status": "not_expected",
        },
        "sensor": {
            "actual": 1,
            "expected": 1,
            "missing": 0,
            "status": "covered",
        },
        "diagnostic": {
            "actual": 1,
            "expected": 1,
            "missing": 0,
            "status": "covered",
        },
        "config": {
            "actual": 0,
            "expected": 0,
            "missing": 0,
            "status": "not_expected",
        },
        "event": {
            "actual": 1,
            "expected": 4,
            "missing": 3,
            "status": "missing_from_registry",
        },
        "state_evidence": {
            "params_count": 0,
            "model_components_count": 0,
            "model_events_count": 0,
            "model_properties_count": 0,
            "instance_state_keys_count": 0,
            "status": "online_only",
        },
        "summary": (
            "registry stale: 3 missing and 1 stale/extra; "
            "current_projection_differs_from_ha_registry"
        ),
    }


def test_markdown_report_lists_missing_entity_samples() -> None:
    """Markdown action bucket 应列出 stale 设备缺哪些实体."""
    classified = classify_report({
        "devices": [
            {
                "name": "四键",
                "category": "scene_panel",
                "missing_total": 1,
                "missing_platforms": {"event": 1},
                "missing_samples": [
                    {
                        "platform": "event",
                        "name": "按键一事件",
                        "component_id": "scene_panel_1",
                        "entity_category": "primary",
                        "role": "event",
                    }
                ],
            }
        ]
    })

    markdown = markdown_report(classified)

    assert "Missing entity samples" in markdown
    assert "Missing/Extra" in markdown
    assert "Roles" in markdown
    assert "Platforms" in markdown
    assert "Extra device entities" in markdown
    assert "Schema gaps" in markdown
    assert "platform=event" in markdown
    assert "name=按键一事件" in markdown
    assert "component_id=scene_panel_1" in markdown


def test_markdown_report_shows_installed_runtime_drift() -> None:
    """Markdown 摘要应显式展示本地 HA 安装态是否与源码一致。"""
    classified = classify_report({
        "install_runtime": {"matched_source": False, "changed_files": 1},
        "devices": [
            {
                "name": "四键",
                "missing_total": 1,
                "missing_platforms": {"event": 1},
            }
        ],
    })

    markdown = markdown_report(classified)

    assert "Installed runtime matches source: false" in markdown
    assert "Installed Runtime Drift (1)" in markdown
    assert "sync_or_reload_installed_runtime" in markdown
