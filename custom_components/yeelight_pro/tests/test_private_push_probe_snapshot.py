"""Private push probe subscribe-snapshot diagnostics tests."""

from __future__ import annotations

from pathlib import Path

from aiohttp import WSMsgType
import pytest

from scripts.private_push_probe.models import ProbeSummary, TopologySnapshot
from scripts.private_push_probe.push_probe import handle_message, record_control_frame
from scripts.private_push_probe.snapshot import (
    subscribe_snapshot_samples,
    subscribe_snapshot_summary,
    subscribe_topology_coverage,
    unsafe_subscribe_snapshot_details,
)
from scripts.private_push_probe.cli import build_report, push_endpoint_summary

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
                    "field": "deviceId",
                    "hash": "ae7ac0cc1cbc2b02",
                    "collections": ["data"],
                }
            ],
            "identity_candidate_fields": ["id", "deviceId"],
            "loaded_identity_fields": ["deviceId"],
            "loaded_relation_fields": [],
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
            "identity_candidate_fields": [],
            "loaded_identity_fields": [],
            "loaded_relation_fields": [],
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


def test_subscribe_snapshot_unsafe_details_are_explicitly_raw() -> None:
    """unsafe 本地明细用于手动排查订阅范围，允许暴露原始节点信息."""
    topology = TopologySnapshot(
        data={
            228233: {
                "id": 228233,
                "deviceId": 228233,
                "name": "四键开关",
                "category": "scene_panel",
                "type": 2,
                "pid": 1509378,
            }
        },
        gateways={},
        groups=[],
        rooms=[{"id": 1001, "name": "客厅"}],
        areas=[],
        houses=[{"id": 2001, "name": "样板家庭"}],
        filter_config=None,
        hydration={},
        endpoint_errors={},
    )
    payload = {
        "result": "ok",
        "data": {
            "method": "subscribe",
            "devices": [
                {"id": 1, "deviceId": 228233, "nt": 2, "o": True},
                {"id": 2, "roomId": 1001, "houseId": 2001},
            ],
        },
    }

    details = unsafe_subscribe_snapshot_details(payload, topology)

    assert details[0]["candidates"][1] == {
        "field": "deviceId",
        "value": 228233,
        "matches": [
            {
                "collection": "data",
                "id": 228233,
                "deviceId": 228233,
                "name": "四键开关",
                "category": "scene_panel",
                "type": 2,
                "pid": 1509378,
            }
        ],
    }
    assert details[0]["snapshot"] == {"id": 1, "deviceId": 228233}
    assert details[1]["candidates"][1]["matches"] == [
        {"collection": "rooms", "id": 1001, "name": "客厅"}
    ]
    assert details[1]["candidates"][2]["matches"] == [
        {"collection": "houses", "id": 2001, "name": "样板家庭"}
    ]


def test_probe_summary_records_unsafe_subscribe_details_only_when_enabled() -> None:
    """unsafe 订阅明细必须由调用方显式开启，默认报告保持脱敏."""
    topology = TopologySnapshot(
        data={228233: {"id": 228233, "deviceId": 228233, "name": "四键开关"}},
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
                    {
                        "id": 1,
                        "deviceId": 228233,
                        "name": "订阅行",
                        "pid": 1509378,
                    }
                ],
            },
        },
        unsafe_local_details=True,
    )

    result = summary.as_dict()
    assert result["unsafe_subscribe_details"][0]["snapshot"] == {
        "id": 1,
        "deviceId": 228233,
        "name": "订阅行",
        "pid": 1509378,
    }
    assert result["unsafe_subscribe_details"][0]["candidates"][1]["value"] == 228233
    assert result["unsafe_subscribe_details"][0]["candidates"][1]["matches"][0][
        "name"
    ] == "四键开关"


def test_subscribe_snapshot_summary_is_aggregate_only() -> None:
    """订阅快照摘要只输出数量和字段名，不暴露原始节点值."""
    topology = TopologySnapshot(
        data={228233: {"id": 228233, "deviceId": 228233}},
        gateways={},
        groups=[],
        rooms=[{"id": 1001}],
        areas=[],
        houses=[{"id": 2001}],
        filter_config=None,
        hydration={},
        endpoint_errors={},
    )
    payload = {
        "result": "ok",
        "data": {
            "method": "subscribe",
            "devices": [
                {"id": 1, "deviceId": 228233, "nt": 2, "params": {"p": True}},
                {"id": 2, "roomId": 1001, "houseId": 2001},
                {"params": {"o": False}},
            ],
        },
    }

    result = subscribe_snapshot_summary(payload, topology)

    assert result == {
        "device_count": 3,
        "state_device_count": 2,
        "no_candidate_count": 1,
        "selected_loaded_count": 0,
        "loaded_candidate_rows": 2,
        "identity_candidate_rows": 2,
        "identity_loaded_rows": 1,
        "relation_only_rows": 1,
        "rows_without_loaded_candidates": 1,
        "valid_candidate_rows": 1,
        "rows_without_valid_candidate": 2,
        "maybe_filtered_count": 0,
        "node_types": {"2": 1, "none": 2},
        "state_keys": {"params": 2},
        "selected_collections": {},
        "candidate_counts": {"0": 1, "2": 1, "3": 1},
        "valid_candidate_counts": {"0": 2, "1": 1},
        "loaded_candidate_counts": {"0": 1, "1": 1, "2": 1},
    }
    assert "228233" not in str(result)
    assert "1001" not in str(result)
    assert "2001" not in str(result)


def test_subscribe_topology_coverage_reports_uncovered_loaded_nodes() -> None:
    """订阅覆盖矩阵应说明快照覆盖了哪些拓扑集合和品类."""
    topology = TopologySnapshot(
        data={
            228233: {
                "id": 228233,
                "deviceId": 228233,
                "name": "四键开关",
                "category": "scene_panel",
            },
            228234: {
                "id": 228234,
                "deviceId": 228234,
                "name": "色温灯",
                "category": "light",
            },
        },
        gateways={300001: {"id": 300001, "name": "网关", "category": "gateway"}},
        groups=[{"id": 7001, "name": "灯组"}],
        rooms=[],
        areas=[],
        houses=[],
        filter_config=None,
        hydration={},
        endpoint_errors={},
    )
    samples = subscribe_snapshot_samples(
        {
            "result": "ok",
            "data": {
                "method": "subscribe",
                "devices": [
                    {"id": 228233, "deviceId": 228233},
                    {"id": 300001},
                ],
            },
        },
        topology,
    )

    result = subscribe_topology_coverage(samples, topology)

    assert result["loaded_total"] == 4
    assert result["covered_total"] == 2
    assert result["uncovered_total"] == 2
    assert result["loaded_counts"] == {
        "areas": 0,
        "data": 2,
        "gateways": 1,
        "groups": 1,
        "houses": 0,
        "rooms": 0,
    }
    assert result["covered_counts"]["data"] == 1
    assert result["covered_counts"]["gateways"] == 1
    assert result["uncovered_counts"]["data"] == 1
    assert result["uncovered_counts"]["groups"] == 1
    assert result["covered_category_counts"]["data"] == {"scene_panel": 1}
    assert result["uncovered_category_counts"]["data"] == {"light": 1}
    assert result["covered_category_counts"]["gateways"] == {"gateway": 1}
    assert result["uncovered_category_counts"]["groups"] == {"groups": 1}
    assert "四键开关" not in str(result)
    assert "色温灯" not in str(result)
    assert "228234" not in str(result)


def test_subscribe_topology_coverage_can_include_unsafe_uncovered_details() -> None:
    """unsafe 模式可输出未覆盖节点本地明细，便于私有环境排查."""
    topology = TopologySnapshot(
        data={
            228233: {
                "id": 228233,
                "deviceId": 228233,
                "name": "四键开关",
                "category": "scene_panel",
            },
            228234: {
                "id": 228234,
                "deviceId": 228234,
                "name": "色温灯",
                "category": "light",
            },
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
    samples = subscribe_snapshot_samples(
        {
            "result": "ok",
            "data": {
                "method": "subscribe",
                "devices": [{"id": 228233, "deviceId": 228233}],
            },
        },
        topology,
    )

    result = subscribe_topology_coverage(
        samples,
        topology,
        unsafe_local_details=True,
    )

    assert result["unsafe_uncovered_details"] == {
        "data": [
            {
                "id": 228234,
                "deviceId": 228234,
                "name": "色温灯",
                "category": "light",
            }
        ]
    }


def test_push_endpoint_summary_labels_dev_and_test_routes_without_raw_host() -> None:
    """probe 报告应标明 dev/test 路由，但不能输出私有 endpoint 明文."""

    dev = push_endpoint_summary("ws://192.168.1.202:7779/ws")
    test = push_endpoint_summary("ws://192.168.0.89:7779/ws")

    assert dev == {
        "scheme": "ws",
        "path": "/ws",
        "host_hash": "22467f9e45c3766e",
        "known_route": "private_dev_direct",
    }
    assert test == {
        "scheme": "ws",
        "path": "/ws",
        "host_hash": "563beb7fb019fd0e",
        "known_route": "private_test_direct",
    }
    assert "192.168" not in str(dev)
    assert "192.168" not in str(test)


def test_build_report_marks_unsafe_local_details() -> None:
    """CLI 报告必须显式标注是否包含本地不安全明细."""
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

    report = build_report(
        {"entry_id": "entry-1", "data": {}},
        {"connection_mode": "private", "house_id": 1},
        topology,
        ProbeSummary(),
        "ws://192.168.1.202:7779/ws",
        unsafe_local_details=True,
    )

    assert report["report_safety"] == {"unsafe_local_details": True}
