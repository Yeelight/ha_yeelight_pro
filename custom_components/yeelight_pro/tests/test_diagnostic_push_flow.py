"""Push payload-flow diagnostic status tests."""

from __future__ import annotations

from custom_components.yeelight_pro.diagnostic_push_flow import (
    data_import_filter_check,
    push_sync_status,
)


def _manager_health() -> dict[str, object]:
    """Return a running push manager health payload."""
    return {
        "running": True,
        "handled_payloads": 0,
        "last_error_type": None,
    }


def _transport_health(**overrides: object) -> dict[str, object]:
    """Return a connected transport health payload."""
    payload: dict[str, object] = {
        "running": True,
        "websocket_open": True,
        "dispatched_payloads": 0,
        "unsupported_messages": 0,
        "control_frames": 2,
        "last_runtime_error_type": None,
        "last_private_status_result": None,
        "last_private_status_reason": None,
        "private_status_non_success_frames": 0,
    }
    payload.update(overrides)
    return payload


def test_push_sync_status_uses_latest_private_status_result() -> None:
    """历史 private status 失败不应掩盖当前无业务帧状态。"""
    status = push_sync_status(
        _manager_health(),
        _transport_health(
            private_status_non_success_frames=1,
            last_private_status_result="success",
        ),
    )

    assert status == "no_data_payload_received"


def test_push_sync_status_reports_current_private_status_non_success() -> None:
    """最后一次 private status 非成功时仍应明确暴露订阅状态问题。"""
    status = push_sync_status(
        _manager_health(),
        _transport_health(
            private_status_non_success_frames=1,
            last_private_status_result="non_success",
        ),
    )

    assert status == "private_status_non_success"


def test_push_sync_status_reports_no_subscribable_devices_reason() -> None:
    """私有 push 明确返回无可订阅设备时，应给出固定聚合状态。"""
    status = push_sync_status(
        _manager_health(),
        _transport_health(
            private_status_non_success_frames=1,
            last_private_status_result="non_success",
            last_private_status_reason="no_subscribable_devices",
        ),
    )

    assert status == "private_push_no_subscribable_devices"


def test_data_import_filter_check_is_not_applicable_without_data_payload() -> None:
    """没有业务帧时不能误判为导入过滤或节点不匹配。"""
    assert (
        data_import_filter_check(
            _manager_health(),
            _transport_health(dispatched_payloads=0),
            import_filter_active=True,
        )
        == "not_applicable_no_data_payload"
    )


def test_data_import_filter_check_reports_filter_disabled() -> None:
    """导入过滤关闭时，节点未命中也不是过滤导致。"""
    assert (
        data_import_filter_check(
            {"unknown_property_updates": 1},
            _transport_health(
                dispatched_payloads=1,
                recent_data_nodes_matching_loaded_topology=0,
                recent_data_nodes_not_loaded=1,
            ),
            import_filter_active=False,
        )
        == "filter_disabled"
    )


def test_data_import_filter_check_reports_possible_filter_related_miss() -> None:
    """导入过滤开启且业务帧节点未命中时，应明确提示可能被过滤。"""
    assert (
        data_import_filter_check(
            {"unknown_property_updates": 1},
            _transport_health(
                dispatched_payloads=1,
                recent_data_nodes_matching_loaded_topology=0,
                recent_data_nodes_not_loaded=1,
            ),
            import_filter_active=True,
        )
        == "unknown_or_unloaded_nodes_may_be_filtered"
    )
