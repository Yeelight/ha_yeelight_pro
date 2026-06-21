"""Private push probe topology self-check tests."""

from __future__ import annotations

from scripts.private_push_probe.models import TopologySnapshot
from scripts.private_push_probe.push_probe import record_event_payloads
from scripts.private_push_probe.topology import (
    classify_update,
    topology_payload_coverage,
    topology_self_check,
)

from custom_components.yeelight_pro.push import push_property_updates


def test_topology_self_check_exercises_push_parser_and_matcher() -> None:
    """探针自检应完整走 WebSocket prop 解析与拓扑匹配路径。"""
    topology = TopologySnapshot(
        data={
            228216: {
                "id": 228216,
                "deviceId": 228216,
                "name": "Loaded Device",
                "params": {"p": False},
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

    result = topology_self_check(topology)

    assert result["available"] is True
    assert result["matched"] is True
    assert result["synthetic_payload_matched"] is True
    assert result["selected_loaded"] is True
    assert result["maybe_filtered"] is False
    assert result["synthetic_payload_maybe_filtered"] is False
    assert result["synthetic_payload_sample"]["selected_collections"] == ["data"]


def test_topology_self_check_reports_no_loaded_nodes() -> None:
    """没有加载设备时，自检应给出安全聚合原因。"""
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

    assert topology_self_check(topology) == {
        "available": False,
        "matched": False,
        "reason": "no_loaded_device_nodes",
    }


def test_topology_classifier_resolves_loaded_device_id_alias() -> None:
    """真实推送行 ID 不在拓扑时，应能用 deviceId alias 命中设备。"""
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
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 999998,
                    "deviceId": "228233",
                    "nt": 2,
                    "params": {"1-p": False},
                }
            ],
        }
    )

    result = classify_update(updates[0], topology)

    assert result["matched"] is True
    assert result["selected_loaded"] is False
    assert result["alias_resolved"] is True
    assert result["not_loaded"] is False
    assert result["maybe_filtered"] is False
    assert result["sample"]["selected_collections"] == []
    assert result["sample"]["loaded_candidate_count"] == 1
    assert result["sample"]["valid_candidate_count"] == 1
    assert result["sample"]["candidate_hashes"] == [
        {
            "field_label": "identity_device",
            "hash": "ae7ac0cc1cbc2b02",
            "collections": ["data"],
        }
    ]


def test_topology_classifier_marks_loaded_device_that_filter_would_exclude() -> None:
    """导入过滤只作为诊断信号，不能把已加载 payload 误判成未匹配。"""
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
        filter_config={
            "enabled": True,
            "mode": "include",
            "include": {"category": ["light"]},
        },
        hydration={},
        endpoint_errors={},
    )
    update = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": "228233",
                    "nt": 2,
                    "params": {"1-p": False},
                }
            ],
        }
    )[0]

    result = classify_update(update, topology)

    assert result["matched"] is True
    assert result["selected_loaded"] is True
    assert result["not_loaded"] is False
    assert result["maybe_filtered"] is True


def test_topology_payload_coverage_checks_all_loaded_collections() -> None:
    """合成 payload 覆盖检查应遍历当前加载的设备、分组、房间和家庭."""
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
        groups=[{"id": 7001}],
        rooms=[{"id": 8001}],
        areas=[],
        houses=[{"id": 9001}],
        filter_config=None,
        hydration={},
        endpoint_errors={},
    )

    assert topology_payload_coverage(topology) == {
        "available": True,
        "total_nodes": 4,
        "matched_nodes": 4,
        "not_loaded_nodes": 0,
        "maybe_filtered_nodes": 0,
        "parse_failures": 0,
        "by_collection": {
            "data": {
                "total_nodes": 1,
                "matched_nodes": 1,
                "not_loaded_nodes": 0,
                "maybe_filtered_nodes": 0,
                "parse_failures": 0,
            },
            "groups": {
                "total_nodes": 1,
                "matched_nodes": 1,
                "not_loaded_nodes": 0,
                "maybe_filtered_nodes": 0,
                "parse_failures": 0,
            },
            "houses": {
                "total_nodes": 1,
                "matched_nodes": 1,
                "not_loaded_nodes": 0,
                "maybe_filtered_nodes": 0,
                "parse_failures": 0,
            },
            "rooms": {
                "total_nodes": 1,
                "matched_nodes": 1,
                "not_loaded_nodes": 0,
                "maybe_filtered_nodes": 0,
                "parse_failures": 0,
            },
        },
    }


def test_topology_payload_coverage_marks_filter_only_for_devices() -> None:
    """导入过滤只应作为已加载设备的诊断提示，不影响拓扑命中结论."""
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
        groups=[{"id": 7001}],
        rooms=[],
        areas=[],
        houses=[],
        filter_config={
            "enabled": True,
            "mode": "include",
            "include": {"category": ["light"]},
        },
        hydration={},
        endpoint_errors={},
    )

    result = topology_payload_coverage(topology)

    assert result["matched_nodes"] == 2
    assert result["not_loaded_nodes"] == 0
    assert result["maybe_filtered_nodes"] == 1
    assert result["by_collection"]["data"]["maybe_filtered_nodes"] == 1
    assert result["by_collection"]["groups"]["maybe_filtered_nodes"] == 0


def test_topology_payload_coverage_reports_empty_topology() -> None:
    """没有加载任何拓扑节点时，应给出聚合空结果."""
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

    assert topology_payload_coverage(topology) == {
        "available": False,
        "total_nodes": 0,
        "matched_nodes": 0,
        "not_loaded_nodes": 0,
        "maybe_filtered_nodes": 0,
        "parse_failures": 0,
        "by_collection": {},
    }


def test_push_probe_records_event_payload_topology_alias_match() -> None:
    """事件推送也要检查 source id/candidates 是否命中已导入拓扑。"""
    from scripts.private_push_probe.models import ProbeSummary

    topology = TopologySnapshot(
        data={
            228233: {
                "id": 228233,
                "deviceId": 228233,
                "category": "scene_panel",
                "params": {},
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

    record_event_payloads(
        summary,
        topology,
        {
            "type": "event",
            "nodes": [
                {
                    "id": 999998,
                    "deviceId": "228233",
                    "nt": 2,
                    "event": "panel.click",
                    "params": {"key": 1},
                }
            ],
        },
    )

    assert summary.event_payloads == 1
    assert summary.event_matched_loaded_topology == 1
    assert summary.event_selected_id_loaded == 0
    assert summary.event_alias_resolved_matches == 1
    assert summary.event_not_loaded == 0
    assert summary.event_samples == [
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
            "maybe_filtered": False,
            "event_type": "panel.click",
        }
    ]
