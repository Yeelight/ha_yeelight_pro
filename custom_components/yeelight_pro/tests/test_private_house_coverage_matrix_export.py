"""Private-house coverage matrix export tests."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys

from scripts.export_private_house_coverage_matrix import main as export_matrix_main
from scripts.private_house_audit.classification import (
    ACTION_REGISTRY_REFRESH,
    ACTION_SYNC_RUNTIME,
    STATUS_REGISTRY_STALE,
    STATUS_RUNTIME_DRIFT,
)


def test_export_private_house_coverage_matrix_writes_csv(tmp_path: Path) -> None:
    """分类 JSON 应可导出逐设备 CSV，便于全量人工核查."""
    classification = tmp_path / "classification.json"
    output = tmp_path / "classification.csv"
    classification.write_text(
        json.dumps(
            {
                "devices": [
                    {
                        "name": "四键",
                        "category": "scene_panel",
                        "type": "8390664",
                        "pid": 8390664,
                        "online": True,
                        "product_schema": False,
                        "product_model": True,
                        "device_instance": True,
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
                            "device_instance_available": True,
                        },
                        "coverage_view": {
                            "control": {
                                "expected": 0,
                                "actual": 0,
                                "missing": 0,
                                "status": "not_expected",
                            },
                            "sensor": {
                                "expected": 1,
                                "actual": 1,
                                "missing": 0,
                                "status": "covered",
                            },
                            "diagnostic": {
                                "expected": 1,
                                "actual": 1,
                                "missing": 0,
                                "status": "covered",
                            },
                            "config": {
                                "expected": 0,
                                "actual": 0,
                                "missing": 0,
                                "status": "not_expected",
                            },
                            "event": {
                                "expected": 4,
                                "actual": 1,
                                "missing": 3,
                                "status": "missing_from_registry",
                            },
                            "state_evidence": {
                                "status": "covered",
                            },
                            "summary": "registry stale: event entities missing",
                        },
                        "params_count": 2,
                        "model_components_count": 4,
                        "model_properties_count": 4,
                        "model_readable_properties_count": 4,
                        "model_writable_properties_count": 4,
                        "model_events_count": 0,
                        "model_actions_count": 0,
                        "instance_components_count": 4,
                        "instance_state_keys_count": 1,
                        "projected_component_count": 5,
                        "projected_component_ids": [
                            "online_status",
                            "scene_panel_1",
                            "scene_panel_2",
                        ],
                        "schema_gap_reason": "",
                        "low_coverage_reasons": ["registry_missing"],
                        "param_keys": ["p", "k1"],
                        "missing_samples": [
                            {
                                "platform": "event",
                                "name": "按键一事件",
                                "component_id": "scene_panel_1",
                                "entity_category": "primary",
                                "role": "event",
                            }
                        ],
                        "stale_samples": [
                            {
                                "platform": "switch",
                                "name": "旧歌单ID",
                                "component_id": "other_mpml_switch",
                                "entity_category": "config",
                                "role": "config",
                            }
                        ],
                        "conclusion": {
                            "status": STATUS_REGISTRY_STALE,
                            "action": ACTION_REGISTRY_REFRESH,
                            "reason": "expected_entities_missing_from_registry",
                        },
                    }
                ],
                "topology_entities": [
                    {
                        "name": "topology:room",
                        "category": "topology",
                        "actual_total": 1,
                        "expected_total": 1,
                        "missing_total": 0,
                        "expected_roles": {"primary_control_or_state": 1},
                        "actual_roles": {"primary_control_or_state": 1},
                        "expected_platforms": {"light": 1},
                        "actual_platforms": {"light": 1},
                        "missing_platforms": {},
                        "conclusion": {
                            "status": "ok",
                            "action": "no_code_change",
                            "reason": "topology_entities_match_current_registry",
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert export_matrix_main([str(classification), "--output", str(output)]) == 0

    rows = list(csv.DictReader(output.open("r", encoding="utf-8")))
    assert len(rows) == 2
    row = rows[0]
    assert row["device"] == "四键"
    assert row["status"] == STATUS_REGISTRY_STALE
    assert row["action"] == ACTION_REGISTRY_REFRESH
    assert row["coverage_percent"] == "40.0"
    assert row["source_raw_property_count"] == "1"
    assert row["source_raw_property_keys"] == "o"
    assert row["source_product_model_available"] == "true"
    assert row["control_status"] == "not_expected"
    assert row["strict_control_expected"] == "0"
    assert row["strict_control_actual"] == "0"
    assert row["strict_control_missing"] == "0"
    assert row["strict_control_absence_reason"] == (
        "event_input_device_events_are_not_controls"
    )
    assert row["sensor_status"] == "covered"
    assert row["sensor_expected"] == "1"
    assert row["sensor_actual"] == "1"
    assert row["sensor_missing"] == "0"
    assert row["diagnostic_status"] == "covered"
    assert row["event_status"] == "missing_from_registry"
    assert row["state_evidence_status"] == "covered"
    assert row["acceptance_summary"] == "registry stale: event entities missing"
    assert row["diagnostic_expected"] == "1"
    assert row["diagnostic_actual"] == "1"
    assert row["event_expected"] == "4"
    assert row["event_actual"] == "1"
    assert row["event_missing"] == "3"
    assert row["sensor_platforms"] == "sensor=1"
    assert row["diagnostic_platforms"] == "diagnostic=1;platforms=sensor=1"
    assert row["action_required_summary"] == (
        "Reload HA entry to create 3 missing entities (event=3)"
    )
    assert row["expected_roles"] == "diagnostic=1;event=4"
    assert row["actual_platforms"] == "event=1;sensor=1"
    assert row["low_coverage_reasons"] == "registry_missing"
    assert row["param_keys"] == "p|k1"
    assert row["projected_component_ids"] == "online_status|scene_panel_1|scene_panel_2"
    assert row["missing_samples"] == "event/按键一事件/scene_panel_1/primary/event"
    assert row["stale_samples"] == "switch/旧歌单ID/other_mpml_switch/config/config"
    assert rows[1]["device"] == "topology:room"
    assert rows[1]["category"] == "topology"
    assert rows[1]["status"] == "ok"
    assert rows[1]["expected_platforms"] == "light=1"


def test_export_private_house_coverage_matrix_classifies_raw_audit_json(
    tmp_path: Path,
) -> None:
    """矩阵导出直接接收原始 audit JSON 时也必须保留逐设备结论."""
    report = tmp_path / "audit.json"
    output = tmp_path / "audit.csv"
    report.write_text(
        json.dumps(
            {
                "devices": [
                    {
                        "name": "P20 全景屏",
                        "category": "other",
                        "actual_total": 0,
                        "expected_total": 5,
                        "missing_total": 5,
                        "missing_platforms": {"number": 2, "sensor": 1, "switch": 2},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert export_matrix_main([str(report), "--output", str(output)]) == 0

    rows = list(csv.DictReader(output.open("r", encoding="utf-8")))
    assert rows[0]["device"] == "P20 全景屏"
    assert rows[0]["status"] == STATUS_REGISTRY_STALE
    assert rows[0]["action"] == ACTION_REGISTRY_REFRESH
    assert rows[0]["reason"] == "current_projection_differs_from_ha_registry"
    assert rows[0]["action_required_summary"] == (
        "Reload HA entry to create 5 missing entities "
        "(number=2;sensor=1;switch=2)"
    )


def test_export_private_house_coverage_matrix_marks_runtime_drift_first(
    tmp_path: Path,
) -> None:
    """安装态落后时 CSV 应提示先同步/重载 runtime。"""
    report = tmp_path / "audit.json"
    output = tmp_path / "audit.csv"
    report.write_text(
        json.dumps(
            {
                "install_runtime": {
                    "matched_source": False,
                    "changed_files": 1,
                    "changed_samples": ["dynamic_entities.py"],
                },
                "devices": [
                    {
                        "name": "四键",
                        "category": "scene_panel",
                        "actual_total": 2,
                        "expected_total": 5,
                        "missing_total": 3,
                        "missing_platforms": {"event": 3},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert export_matrix_main([str(report), "--output", str(output)]) == 0

    rows = list(csv.DictReader(output.open("r", encoding="utf-8")))
    assert rows[0]["status"] == STATUS_RUNTIME_DRIFT
    assert rows[0]["action"] == ACTION_SYNC_RUNTIME
    assert rows[0]["reason"] == "installed_runtime_differs_from_source"
    assert rows[0]["action_required_summary"] == (
        "Sync installed HA runtime from source, then reload the entry"
    )


def test_export_private_house_coverage_matrix_script_runs_directly(
    tmp_path: Path,
) -> None:
    """导出脚本应能作为 python scripts/*.py 直接运行."""
    root = Path(__file__).resolve().parents[3]
    report = tmp_path / "audit.json"
    output = tmp_path / "audit.csv"
    report.write_text(
        json.dumps(
            {
                "devices": [
                    {
                        "name": "四键",
                        "category": "scene_panel",
                        "actual_total": 2,
                        "expected_total": 5,
                        "missing_total": 3,
                        "missing_platforms": {"event": 3},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "export_private_house_coverage_matrix.py"),
            str(report),
            "--output",
            str(output),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rows = list(csv.DictReader(output.open("r", encoding="utf-8")))
    assert rows[0]["status"] == STATUS_REGISTRY_STALE
    assert rows[0]["action"] == ACTION_REGISTRY_REFRESH
