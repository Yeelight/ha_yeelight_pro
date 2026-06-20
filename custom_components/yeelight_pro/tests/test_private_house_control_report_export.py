"""Private-house control-first Markdown report export tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.export_private_house_control_report import (
    main as export_control_report_main,
    render_control_report,
)


def test_render_control_report_summarizes_missing_controls_and_source_limits() -> None:
    """控制优先报告应突出缺控设备和源数据不足设备."""
    report = render_control_report({
        "summary": {
            "device_count": 2,
            "statuses": {"ok": 1, "source_data_limited": 1},
            "audit": {
                "expected_entities": 4,
                "actual_device_entities": 4,
                "missing_entities": 0,
                "expected_topology_entities": 1,
                "actual_topology_entities": 1,
                "missing_topology_entities": 0,
            },
            "install_runtime": {"matched_source": True},
        },
        "devices": [
            {
                "name": "智能开关-四键",
                "category": "relay_switch",
                "actual_total": 5,
                "expected_total": 5,
                "actual_platforms": {"sensor": 1, "switch": 4},
                "coverage_view": {
                    "control": {
                        "expected": 4,
                        "actual": 4,
                        "missing": 0,
                        "status": "covered",
                    },
                    "diagnostic": {
                        "expected": 1,
                        "actual": 1,
                        "missing": 0,
                        "status": "covered",
                    },
                    "sensor": {
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
                        "expected": 0,
                        "actual": 0,
                        "missing": 0,
                        "status": "not_expected",
                    },
                },
                "conclusion": {"status": "ok"},
            },
            {
                "name": "未知灯具",
                "category": "unknown",
                "pid": 123,
                "actual_total": 1,
                "expected_total": 1,
                "params_count": 1,
                "param_keys": ["o"],
                "product_model": False,
                "product_schema": False,
                "coverage_view": {
                    "control": {
                        "expected": 0,
                        "actual": 0,
                        "missing": 0,
                        "status": "not_expected",
                    },
                    "diagnostic": {
                        "expected": 1,
                        "actual": 1,
                        "missing": 0,
                        "status": "covered",
                    },
                    "sensor": {
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
                        "expected": 0,
                        "actual": 0,
                        "missing": 0,
                        "status": "not_expected",
                    },
                },
                "conclusion": {
                    "status": "source_data_limited",
                    "reason": "open_api_payload_has_only_online_or_unknown_capability_evidence",
                },
            },
        ],
        "topology_entities": [
            {
                "source": "room",
                "actual_total": 1,
                "expected_total": 1,
                "actual_roles": {"primary_control_or_state": 1},
                "actual_platforms": {"light": 1},
                "conclusion": {"status": "ok"},
            }
        ],
    })

    assert "Devices reviewed: 2" in report
    assert "Control missing devices: 0" in report
    assert "Missing-control device list: None" in report
    assert "Source-data-limited devices needing upstream/product-model evidence: 1" in report
    assert "| 1 | 未知灯具 | unknown | 123 | 1/1 |" in report
    assert "智能开关-四键" in report
    assert "4/4 covered" in report
    assert "control platforms: switch=4" in report
    assert "| 1 | room | 1/1 | primary_control_or_state=1 | light=1 | ok |" in report


def test_export_private_house_control_report_classifies_raw_audit_json(
    tmp_path: Path,
) -> None:
    """报告导出可直接接收原始 audit JSON。"""
    report = tmp_path / "audit.json"
    output = tmp_path / "control.md"
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

    assert export_control_report_main([str(report), "--output", str(output)]) == 0

    text = output.read_text(encoding="utf-8")
    assert "# Yeelight Pro Private House Control Coverage" in text
    assert "P20 全景屏" in text
    assert "registry_stale" in text


def test_export_private_house_control_report_script_runs_directly(
    tmp_path: Path,
) -> None:
    """导出脚本应能作为 python scripts/*.py 直接运行."""
    root = Path(__file__).resolve().parents[3]
    report = tmp_path / "classified.json"
    output = tmp_path / "control.md"
    report.write_text(
        json.dumps(
            {
                "devices": [
                    {
                        "name": "四键",
                        "category": "scene_panel",
                        "actual_total": 5,
                        "expected_total": 5,
                        "coverage_view": {
                            "control": {
                                "expected": 0,
                                "actual": 0,
                                "missing": 0,
                                "status": "not_expected",
                            }
                        },
                        "conclusion": {"status": "ok"},
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
            str(root / "scripts" / "export_private_house_control_report.py"),
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
    assert "四键" in output.read_text(encoding="utf-8")
