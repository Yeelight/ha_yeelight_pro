"""Diagnostics-safe log payload helpers for debug push services."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_SAFE_DIGEST_RE = re.compile(r"^[0-9a-f]{8,32}$")


def debug_push_emit_log_payload(summary: Mapping[str, Any]) -> dict[str, Any]:
    """返回调试注入后的聚合结果，不输出原始节点 ID 或属性值。"""
    return _selected_payload(
        summary,
        (
            "input_updates",
            "empty_param_updates",
            "applied_device_updates",
            "unknown_device_updates",
            "group_updates",
            "topology_node_updates",
            "routed_updates",
            "changed",
            "applied_node_samples",
            "unknown_node_samples",
            "affected_contexts",
        ),
    )


def push_health_log_payload(health: Mapping[str, Any] | None) -> dict[str, Any]:
    """压缩 push health 为日志安全的聚合字段。"""
    if not isinstance(health, Mapping):
        return {"push_available": False, "status": "unavailable"}
    payload_flow = _mapping_value(health.get("payload_flow"))
    transport = _mapping_value(health.get("transport"))
    return {
        "push_available": True,
        "status": _safe_label(health.get("push_sync_status")),
        "manager": _selected_payload(
            health,
            (
                "running",
                "handled_payloads",
                "changed_payloads",
                "unchanged_payloads",
                "property_updates",
                "empty_param_updates",
                "applied_property_updates",
                "unknown_property_updates",
                "group_updates",
                "topology_node_updates",
                "routed_property_updates",
                "last_property_update_count",
                "last_dispatched_event_count",
                "last_payload_changed",
                "last_payload_handle_duration_ms",
                "last_listener_notification_count",
                "last_listener_context_count",
                "last_payload_type",
                "last_payload_at",
                "last_error_type",
                "last_applied_node_samples",
                "last_unknown_node_samples",
                "recent_applied_node_samples",
                "recent_unknown_node_samples",
            ),
        ),
        "payload_flow": _selected_payload(
            payload_flow,
            (
                "status",
                "transport_health_available",
                "websocket_open",
                "received_message_count",
                "decoded_json_message_count",
                "control_frame_count",
                "private_status_non_success_count",
                "private_status_reason",
                "unsupported_payload_count",
                "subscribe_sent",
                "subscribe_sent_count",
                "subscribe_snapshot_device_count",
                "subscribe_nodes_matching_loaded_topology",
                "subscribe_nodes_not_loaded",
                "subscribe_loaded_topology_count",
                "subscribe_loaded_topology_coverage",
                "subscribe_topology_check",
                "data_payload_received",
                "data_payload_count",
                "handled_payload_count",
                "property_update_count",
                "last_payload_handle_duration_ms",
                "last_listener_notification_count",
                "last_listener_context_count",
                "last_data_nodes_matching_loaded_topology",
                "last_data_nodes_not_loaded",
                "recent_data_nodes_matching_loaded_topology",
                "recent_data_nodes_not_loaded",
                "data_topology_check",
                "data_import_filter_check",
                "import_filter_active",
            ),
        ),
        "transport": _selected_payload(
            transport,
            (
                "running",
                "websocket_open",
                "connect_attempts",
                "connected_count",
                "disconnected_count",
                "reconnect_attempts",
                "received_messages",
                "decoded_json_messages",
                "dispatched_payloads",
                "ignored_messages",
                "unsupported_messages",
                "malformed_messages",
                "control_frames",
                "private_status_frames",
                "private_status_non_success_frames",
                "subscribe_sent_count",
                "heartbeat_sent_count",
                "reconnect_pending",
                "next_reconnect_delay",
                "last_start_error_type",
                "last_runtime_error_type",
                "last_handshake_status",
                "last_disconnect_reason",
                "last_subscribe_error_type",
                "last_close_code",
                "last_close_exception_type",
                "first_frame_received",
                "last_control_method",
                "last_private_status_result",
                "last_private_status_reason",
                "last_subscribe_device_count",
                "last_subscribe_state_device_count",
                "last_payload_type",
                "last_message_at",
                "last_dispatched_at",
                "last_ignored_reason",
                "last_ignored_payload_type",
            ),
        ),
        "unsupported_payload_shape": _safe_shape_summary(
            transport.get("last_unsupported_payload_shape"),
        ),
    }


def _mapping_value(value: Any) -> Mapping[str, Any]:
    """返回 mapping；非 mapping 视为空。"""
    return value if isinstance(value, Mapping) else {}


def _selected_payload(
    source: Mapping[str, Any],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    """复制白名单聚合字段。"""
    return {
        key: _safe_log_value(source.get(key))
        for key in keys
        if key in source
    }


def _safe_log_value(value: Any) -> Any:
    """只允许标量聚合值进入 debug 日志。"""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        return _safe_sample_list(list(value))
    return _safe_label(value)


def _safe_label(value: Any) -> str | None:
    """返回短标签，避免日志输出对象表示或原始 payload。"""
    if not isinstance(value, str) or not value:
        return None
    return value[:80]


def _safe_shape_summary(value: Any) -> dict[str, Any] | None:
    """返回字段名级别的 unsupported payload shape，不包含字段值。"""
    if not isinstance(value, Mapping):
        return None
    objects = value.get("objects")
    if not isinstance(objects, list):
        return None
    return {
        "objects": [
            {
                "path": _safe_label(item.get("path")),
                "keys": _safe_string_list(item.get("keys")),
                "flags": _safe_bool_mapping(item.get("flags")),
            }
            for item in objects[:5]
            if isinstance(item, Mapping)
        ],
        "status": _safe_status_shape(value.get("status")),
    }


def _safe_status_shape(value: Any) -> dict[str, Any] | None:
    """返回状态文本的安全摘要，不包含原始文本。"""
    if not isinstance(value, Mapping):
        return None
    result_length = value.get("result_length")
    result_hash = value.get("result_hash")
    if not isinstance(result_length, int) or not isinstance(result_hash, str):
        return None
    return {
        "result_length": result_length,
        "result_hash": result_hash[:32],
        "data_keys": _safe_string_list(value.get("data_keys")),
    }


def _safe_string_list(value: Any) -> list[str]:
    """返回有限长度字符串列表。"""
    if not isinstance(value, list):
        return []
    return [
        item[:80]
        for item in value[:20]
        if isinstance(item, str) and item
    ]


def _safe_bool_mapping(value: Any) -> dict[str, bool]:
    """返回布尔 flag mapping。"""
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key)[:80]: bool(flag)
        for key, flag in value.items()
        if isinstance(key, str) and isinstance(flag, bool)
    }


def _safe_sample_list(value: list[Any]) -> list[dict[str, Any]]:
    """返回字段名级别的运行时样本，避免输出原始节点 ID 或属性值。"""
    samples: list[dict[str, Any]] = []
    for item in value[:5]:
        if not isinstance(item, Mapping):
            continue
        sample = _safe_sample(item)
        if sample:
            samples.append(sample)
    return samples


def _safe_sample(item: Mapping[str, Any]) -> dict[str, Any]:
    """白名单复制已脱敏的 push routing 样本。"""
    sample: dict[str, Any] = {}
    if label := _safe_digest_label(item.get("node_id_hash")):
        sample["node_id_hash"] = label
    if isinstance(item.get("node_type"), int):
        sample["node_type"] = item.get("node_type")
    if isinstance(item.get("param_keys"), list):
        sample["param_keys"] = _safe_string_list(item.get("param_keys"))
    if isinstance(item.get("matched_collections"), list):
        sample["matched_collections"] = _safe_string_list(
            item.get("matched_collections")
        )
    if label := _safe_label(item.get("reason")):
        sample["reason"] = label
    if isinstance(item.get("device_import_filter_enabled"), bool):
        sample["device_import_filter_enabled"] = item.get(
            "device_import_filter_enabled"
        )
    return sample


def _safe_digest_label(value: Any) -> str | None:
    """只接受固定格式的非可逆摘要，避免上游误传原始标识。"""
    label = _safe_label(value)
    if label is None or _SAFE_DIGEST_RE.fullmatch(label) is None:
        return None
    return label
