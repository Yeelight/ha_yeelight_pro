"""Private push probe subscribe-snapshot diagnostics tests."""

from __future__ import annotations

from pathlib import Path

from aiohttp import WSMsgType
import pytest

from scripts.private_push_probe.models import ProbeSummary, TopologySnapshot
from scripts.private_push_probe.push_probe import handle_message, record_control_frame
from scripts.private_push_probe.snapshot import (
    subscribe_snapshot_samples,
)

from .push_transport_helpers import FakeMessage


def test_private_push_probe_cli_has_direct_module_entrypoint() -> None:
    """probe CLI 模块应可直接执行，避免 -m 调用静默无输出."""
    source = Path("scripts/private_push_probe/cli.py").read_text(encoding="utf-8")

    assert "PROJECT_ROOT = Path(__file__).resolve().parents[2]" in source
    assert "sys.path.insert(0, str(PROJECT_ROOT))" in source
    assert 'if __name__ == "__main__":' in source
    assert "raise SystemExit(main())" in source


@pytest.mark.asyncio
async def test_handle_message_counts_private_snapshot_state_as_data_payload() -> None:
    """私有订阅快照携带状态时，probe 应按运行时链路统计为可应用 prop."""
    topology = TopologySnapshot(
        data={
            228233: {
                "id": 228233,
                "deviceId": 228233,
                "category": "relay_switch",
                "params": {"1-p": True},
            }
        },
        gateways={},
        groups=[],
        rooms=[],
        areas=[],
        houses=[],
        filter_config=None,
        hydration={},
        endpoint_errors={},
    )
    summary = ProbeSummary()

    await handle_message(
        summary,
        topology,
        FakeMessage(
            WSMsgType.TEXT,
            (
                '{"result":"ok","data":{"method":"subscribe","devices":['
                '{"id":999998,"deviceId":228233,"nt":2,'
                '"params":{"1-p":false}},'
                '{"id":999999,"deviceId":228234,"nt":2}'
                ']}}'
            ),
        ),
    )

    result = summary.as_dict()
    assert result["frames_seen"] == 1
    assert result["control_frames"] == 1
    assert result["data_frames"] == 1
    assert result["prop_updates"] == 1
    assert result["matched_loaded_topology"] == 1
    assert result["alias_resolved_matches"] == 1
    assert result["not_loaded"] == 0
    assert result["unsupported_frames"] == 0
    assert result["subscribe_snapshot_summary"]["device_count"] == 2
    assert result["subscribe_snapshot_summary"]["state_device_count"] == 1
    assert result["subscribe_match"] == {
        "matched_loaded_topology": 1,
        "not_loaded": 1,
    }
    assert result["data_hash_match"] == {"matched_loaded_topology": 1}
    assert "228233" not in str(result)
    assert "999998" not in str(result)


def test_subscribe_snapshot_samples_match_loaded_device_alias() -> None:
    """订阅快照样本应脱敏展示节点 alias 是否命中当前拓扑."""
    topology = TopologySnapshot(
        data={
            228233: {
                "id": 228233,
                "deviceId": 228233,
                "category": "relay_switch",
                "params": {"1-p": True},
            }
        },
        gateways={},
        groups=[],
        rooms=[],
        areas=[],
        houses=[],
        filter_config=None,
        hydration={},
        endpoint_errors={},
    )
    payload = {
        "result": "ok",
        "data": {
            "method": "subscribe",
            "devices": [
                {
                    "id": 999998,
                    "deviceId": "228233",
                    "nt": 2,
                    "params": {"secretValue": True},
                }
            ],
        },
    }

    samples = subscribe_snapshot_samples(payload, topology)

    assert samples == [
        {
            "node_id_hash": "3cb3b39217202d10",
            "node_type": 2,
            "param_keys": [],
            "selected_collections": [],
            "candidate_count": 2,
            "valid_candidate_count": 1,
            "loaded_candidate_count": 1,
            "candidate_hashes": [
                {
                    "field_label": "identity_device",
                    "hash": "ae7ac0cc1cbc2b02",
                    "collections": ["data"],
                }
            ],
            "identity_candidate_labels": ["identity_primary", "identity_device"],
            "loaded_identity_labels": ["identity_device"],
            "loaded_relation_labels": [],
            "maybe_filtered": False,
            "state_keys": ["params"],
        }
    ]
    assert "228233" not in str(samples)
    assert "secretValue" not in str(samples)


def test_subscribe_snapshot_samples_report_rows_without_ids() -> None:
    """没有节点 ID 的订阅快照行也应给出安全诊断，不抛异常."""
    topology = TopologySnapshot(
        data={},
        gateways={},
        groups=[],
        rooms=[],
        areas=[],
        houses=[],
        filter_config=None,
        hydration={},
        endpoint_errors={},
    )
    payload = {
        "result": "ok",
        "data": {
            "method": "subscribe",
            "devices": [{"params": {"p": True}}],
        },
    }

    assert subscribe_snapshot_samples(payload, topology) == [
        {
            "node_id_hash": None,
            "node_type": None,
            "state_keys": ["params"],
            "selected_collections": [],
            "candidate_count": 0,
            "valid_candidate_count": 0,
            "loaded_candidate_count": 0,
            "candidate_hashes": [],
            "identity_candidate_labels": [],
            "loaded_identity_labels": [],
            "loaded_relation_labels": [],
            "maybe_filtered": False,
        }
    ]


def test_probe_summary_records_subscribe_snapshot_samples() -> None:
    """probe 汇总应保留订阅快照脱敏样本，便于定位订阅范围偏差."""
    topology = TopologySnapshot(
        data={228233: {"id": 228233, "deviceId": 228233}},
        gateways={},
        groups=[],
        rooms=[],
        areas=[],
        houses=[],
        filter_config=None,
        hydration={},
        endpoint_errors={},
    )
    summary = ProbeSummary()

    record_control_frame(
        summary,
        topology,
        {
            "result": "ok",
            "data": {
                "method": "subscribe",
                "devices": [
                    {"id": 1, "deviceId": 228233, "nt": 2, "o": True}
                ],
            },
        },
    )

    result = summary.as_dict()
    assert result["subscribe_match"] == {"matched_loaded_topology": 1}
    assert result["subscribe_snapshot_summary"] == {
        "device_count": 1,
        "state_device_count": 1,
        "no_candidate_count": 0,
        "selected_loaded_count": 0,
        "loaded_candidate_rows": 1,
        "identity_candidate_rows": 1,
        "identity_loaded_rows": 1,
        "relation_only_rows": 0,
        "rows_without_loaded_candidates": 0,
        "valid_candidate_rows": 1,
        "rows_without_valid_candidate": 0,
        "maybe_filtered_count": 0,
        "node_types": {"2": 1},
        "state_keys": {"o": 1},
        "selected_collections": {},
        "candidate_counts": {"2": 1},
        "valid_candidate_counts": {"1": 1},
        "loaded_candidate_counts": {"1": 1},
    }
    assert result["subscribe_samples"][0]["loaded_candidate_count"] == 1
    assert result["subscribe_samples"][0]["state_keys"] == ["o"]
    assert result["subscribe_topology_coverage"] == {
        "loaded_total": 1,
        "covered_total": 1,
        "uncovered_total": 0,
        "loaded_counts": {
            "areas": 0,
            "data": 1,
            "gateways": 0,
            "groups": 0,
            "houses": 0,
            "rooms": 0,
        },
        "covered_counts": {
            "areas": 0,
            "data": 1,
            "gateways": 0,
            "groups": 0,
            "houses": 0,
            "rooms": 0,
        },
        "uncovered_counts": {
            "areas": 0,
            "data": 0,
            "gateways": 0,
            "groups": 0,
            "houses": 0,
            "rooms": 0,
        },
        "covered_category_counts": {
            "areas": {},
            "data": {"data": 1},
            "gateways": {},
            "groups": {},
            "houses": {},
            "rooms": {},
        },
        "uncovered_category_counts": {
            "areas": {},
            "data": {},
            "gateways": {},
            "groups": {},
            "houses": {},
            "rooms": {},
        },
        "covered_hash_samples": {
            "areas": [],
            "data": ["ae7ac0cc1cbc2b02"],
            "gateways": [],
            "groups": [],
            "houses": [],
            "rooms": [],
        },
        "uncovered_hash_samples": {
            "areas": [],
            "data": [],
            "gateways": [],
            "groups": [],
            "houses": [],
            "rooms": [],
        },
    }
    assert "228233" not in str(result)
    assert "unsafe_subscribe_details" not in result
