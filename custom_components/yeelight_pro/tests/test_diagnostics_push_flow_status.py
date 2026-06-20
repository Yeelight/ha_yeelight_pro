"""Diagnostics push-flow status boundary tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.diagnostics import async_get_config_entry_diagnostics
from custom_components.yeelight_pro.push_manager import PushManager

from .diagnostics_helpers import (
    build_aggregate_runtime_coordinator,
    build_diagnostics_entry,
    install_runtime_entry,
)
from .diagnostics_push_helpers import (
    _payload_flow,
    _push_health,
    _TransportWithHealth,
)


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_reports_polling_fallback_when_push_is_disconnected(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """WebSocket 未连接时应明确诊断为实时推送不可用并退回轮询。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(websocket_open=False),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id].update(
        {
            "client": MagicMock(),
            "push_manager": manager,
        }
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    health = data["runtime"]["health"]
    capabilities = data["runtime"]["client_capabilities"]

    assert health["live_updates_intended"] is True
    assert health["live_updates_active"] is False
    assert health["polling_fallback_active"] is True
    assert health["polling_fallback_interval_seconds"] == 15
    assert health["push"]["push_sync_status"] == "not_connected"
    assert health["push"]["transport"]["websocket_open"] is False
    assert health["push"]["transport"]["received_messages"] == 0
    assert health["push"]["transport"]["last_runtime_error_type"] == (
        "WSServerHandshakeError"
    )
    assert health["push"]["transport"]["last_handshake_status"] == 403
    assert health["push"]["transport"]["last_disconnect_reason"] == "handshake_failed"
    assert capabilities["cloud_http_polling"] is True
    assert capabilities["websocket_transport_runtime"] is False
    assert capabilities["websocket_event_notifications"] is False

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_control_frame_error_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """订阅/心跳控制帧错误应区别于普通断线和业务 payload 缺失。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            websocket_open=False,
            last_runtime_error_type="PushControlFrameError",
            control_frames=2,
        ),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    push = data["runtime"]["health"]["push"]
    assert push["push_sync_status"] == "control_frame_error"
    assert push["payload_flow"] == _payload_flow(
        status="control_frame_error",
        websocket_open=False,
        received_message_count=0,
        decoded_json_message_count=0,
        control_frame_count=2,
        subscribe_sent=False,
        subscribe_sent_count=0,
        subscribe_snapshot_device_count=None,
        subscribe_loaded_topology_coverage=None,
        subscribe_topology_check="not_applicable_no_subscribe_snapshot",
        import_filter_active=True,
    )
    assert push["transport"]["last_runtime_error_type"] == "PushControlFrameError"
    assert push["transport"]["control_frames"] == 2

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_includes_push_transport_health(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """诊断应包含 WebSocket transport 聚合计数，便于排查事件通知延迟."""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(coordinator, _TransportWithHealth(dispatched_payloads=1))
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"]["push"] == {
        **_push_health(running=True, started_count=1),
        "push_sync_status": "data_payload_not_handled",
        "payload_flow": _payload_flow(
            status="data_payload_not_handled",
            data_payload_received=True,
            data_payload_count=1,
            last_data_nodes_matching_loaded_topology=1,
                recent_data_nodes_matching_loaded_topology=1,
                data_topology_check="matched_loaded_topology",
                data_import_filter_check="no_filter_related_miss_detected",
                import_filter_active=True,
            ),
        "transport": {
            "running": True,
            "websocket_open": True,
            "connect_attempts": 1,
            "connected_count": 1,
            "disconnected_count": 0,
            "reconnect_attempts": 0,
            "received_messages": 2,
            "decoded_json_messages": 2,
            "dispatched_payloads": 1,
            "ignored_messages": 1,
            "unsupported_messages": 0,
            "malformed_messages": 0,
            "control_frames": 1,
            "private_status_frames": 0,
            "private_status_non_success_frames": 0,
            "subscribe_sent_count": 1,
            "heartbeat_sent_count": 0,
            "pre_first_frame_abnormal_close_count": 0,
            "consecutive_pre_first_frame_abnormal_close_count": 0,
            "reconnect_pending": False,
            "next_reconnect_delay": None,
            "last_start_error_type": None,
            "last_runtime_error_type": None,
            "last_handshake_status": None,
            "last_disconnect_reason": None,
            "last_subscribe_error_type": None,
            "last_close_code": None,
            "last_close_exception_type": None,
            "first_frame_received": True,
            "last_control_method": "subscribe",
            "last_private_status_result": None,
            "last_private_status_reason": None,
            "last_subscribe_device_count": 0,
            "last_subscribe_state_device_count": 0,
            "last_subscribe_state_key_samples": [],
            "last_subscribe_node_hash_samples": [],
            "last_subscribe_node_candidate_hash_samples": [],
            "loaded_topology_node_hash_count": 9,
            "last_subscribe_nodes_matching_loaded_topology": 0,
            "last_subscribe_nodes_not_loaded": 0,
            "last_data_node_hash_samples": ["41cf3c54b6edb00d"],
            "last_data_node_candidate_hash_samples": [["41cf3c54b6edb00d"]],
            "last_data_nodes_matching_loaded_topology": 1,
            "last_data_nodes_not_loaded": 0,
            "recent_data_node_hash_samples": ["41cf3c54b6edb00d"],
            "recent_data_node_candidate_hash_samples": [["41cf3c54b6edb00d"]],
            "recent_data_nodes_matching_loaded_topology": 1,
            "recent_data_nodes_not_loaded": 0,
            "last_payload_type": "prop",
            "last_ignored_reason": None,
            "last_ignored_payload_type": None,
            "last_unsupported_payload_shape": None,
            "last_subscribe_sent_at": 122.0,
            "last_message_at": 123.0,
            "last_dispatched_at": 124.0,
        },
    }

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_no_data_payload_received_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """WebSocket 已连接但未收到业务帧时，应明确不是节点匹配问题。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(dispatched_payloads=0),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"]["push"]["push_sync_status"] == (
        "no_data_payload_received"
    )
    assert data["runtime"]["health"]["push"]["payload_flow"] == _payload_flow(
        status="no_data_payload_received",
        data_topology_check="not_applicable_no_data_payload",
        import_filter_active=True,
    )

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_subscribed_snapshot_without_business_payload(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """订阅快照存在但无 prop/event 帧时，状态仍应指向服务端未推业务帧."""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=0,
            received_messages=10,
            decoded_json_messages=10,
            control_frames=10,
            subscribe_device_count=9,
            subscribe_state_device_count=0,
        ),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    push = data["runtime"]["health"]["push"]
    assert push["push_sync_status"] == "no_data_payload_received"
    assert push["payload_flow"] == _payload_flow(
        status="no_data_payload_received",
        received_message_count=10,
        decoded_json_message_count=10,
        control_frame_count=10,
        subscribe_snapshot_device_count=9,
        subscribe_nodes_matching_loaded_topology=0,
        subscribe_loaded_topology_count=9,
        subscribe_loaded_topology_coverage=0.0,
        subscribe_topology_check="subscribe_snapshot_not_in_loaded_topology",
        data_topology_check="not_applicable_no_data_payload",
        data_import_filter_check="not_applicable_no_data_payload",
        import_filter_active=True,
    )
    assert push["transport"]["last_subscribe_device_count"] == 9
    assert push["transport"]["last_subscribe_state_device_count"] == 0
    assert push["transport"]["dispatched_payloads"] == 0

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_partial_subscribe_topology_coverage(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """订阅快照只覆盖少量拓扑节点时，应明确报告覆盖不足。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=0,
            received_messages=3,
            decoded_json_messages=3,
            control_frames=3,
            subscribe_device_count=1,
            subscribe_state_device_count=0,
            subscribe_node_hashes=["41cf3c54b6edb00d"],
            subscribe_node_candidate_hashes=[["41cf3c54b6edb00d"]],
        ),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    payload_flow = data["runtime"]["health"]["push"]["payload_flow"]
    assert payload_flow["subscribe_snapshot_device_count"] == 1
    assert payload_flow["subscribe_nodes_matching_loaded_topology"] == 1
    assert payload_flow["subscribe_loaded_topology_count"] == 9
    assert payload_flow["subscribe_loaded_topology_coverage"] == 0.1111
    assert payload_flow["subscribe_topology_check"] == (
        "subscribe_snapshot_partial_loaded_topology"
    )

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_private_status_non_success_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """私有 push 返回非成功状态且无业务帧时，应区别于节点匹配失败。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=0,
            private_status_non_success_frames=1,
        ),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    push = data["runtime"]["health"]["push"]
    assert push["push_sync_status"] == "private_status_non_success"
    assert push["payload_flow"] == _payload_flow(
        status="private_status_non_success",
        private_status_non_success_count=1,
        data_topology_check="not_applicable_no_data_payload",
        import_filter_active=True,
    )
    assert push["transport"]["last_private_status_result"] == "non_success"
    assert push["transport"]["last_private_status_reason"] is None
    assert push["transport"]["private_status_non_success_frames"] == 1

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_no_subscribable_devices_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """私有 push 明确没有可订阅设备时，应区别于 HA 拓扑/过滤问题。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=0,
            private_status_non_success_frames=1,
            private_status_reason="no_subscribable_devices",
        ),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    push = data["runtime"]["health"]["push"]
    assert push["push_sync_status"] == "private_push_no_subscribable_devices"
    assert push["payload_flow"] == _payload_flow(
        status="private_push_no_subscribable_devices",
        private_status_non_success_count=1,
        private_status_reason="no_subscribable_devices",
        data_topology_check="not_applicable_no_data_payload",
        import_filter_active=True,
    )
    assert push["transport"]["last_private_status_reason"] == (
        "no_subscribable_devices"
    )

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_unsupported_payload_received_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """收到未识别 JSON 帧时，应和完全没有业务帧区分开。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(dispatched_payloads=0, unsupported_messages=2),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    push = data["runtime"]["health"]["push"]
    assert push["push_sync_status"] == "unsupported_payload_received"
    assert push["payload_flow"] == _payload_flow(
        status="unsupported_payload_received",
        unsupported_payload_count=2,
        data_topology_check="not_applicable_no_data_payload",
        import_filter_active=True,
    )
    assert push["transport"]["unsupported_messages"] == 2

    await manager.async_stop()
