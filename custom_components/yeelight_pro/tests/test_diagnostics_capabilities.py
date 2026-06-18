"""Diagnostics client capability boundary tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import CONNECTION_MODE_CLOUD, DOMAIN
from custom_components.yeelight_pro.diagnostics import async_get_config_entry_diagnostics
from custom_components.yeelight_pro.entry_setup import OptionalRuntimeStartupFailure
from custom_components.yeelight_pro.push_manager import PushManager

from .diagnostics_helpers import (
    build_aggregate_runtime_coordinator,
    build_diagnostics_entry,
    install_runtime_entry,
)


def _push_health(**overrides: object) -> dict[str, object]:
    """Return default push health diagnostics with optional overrides."""
    data: dict[str, object] = {
        "running": False,
        "started_count": 0,
        "stopped_count": 0,
        "handled_payloads": 0,
        "changed_payloads": 0,
        "unchanged_payloads": 0,
        "property_updates": 0,
        "applied_property_updates": 0,
        "unknown_property_updates": 0,
        "group_updates": 0,
        "topology_node_updates": 0,
        "dispatched_events": 0,
        "last_property_update_count": 0,
        "last_dispatched_event_count": 0,
        "last_payload_changed": False,
        "last_payload_type": None,
        "last_payload_at": None,
        "last_error_type": None,
    }
    data.update(overrides)
    return data


class _TransportHealth:
    """Transport health double used by diagnostics tests."""

    def __init__(self, *, websocket_open: bool = True) -> None:
        """Initialize aggregate transport health state."""
        self._websocket_open = websocket_open

    def as_dict(self) -> dict[str, object]:
        """Return aggregate-only transport diagnostics."""
        return {
            "running": True,
            "websocket_open": self._websocket_open,
            "connect_attempts": 1,
            "connected_count": int(self._websocket_open),
            "disconnected_count": int(not self._websocket_open),
            "reconnect_attempts": 0,
            "received_messages": 2 if self._websocket_open else 0,
            "decoded_json_messages": 2 if self._websocket_open else 0,
            "dispatched_payloads": 1 if self._websocket_open else 0,
            "ignored_messages": 1 if self._websocket_open else 0,
            "malformed_messages": 0,
            "control_frames": 1 if self._websocket_open else 0,
            "subscribe_sent_count": 1 if self._websocket_open else 0,
            "heartbeat_sent_count": 0,
            "pre_first_frame_abnormal_close_count": 0,
            "consecutive_pre_first_frame_abnormal_close_count": 0,
            "reconnect_pending": False,
            "reconnect_suspended": False,
            "next_reconnect_delay": None,
            "last_start_error_type": None,
            "last_runtime_error_type": None
            if self._websocket_open
            else "WSServerHandshakeError",
            "last_handshake_status": None if self._websocket_open else 403,
            "last_disconnect_reason": None
            if self._websocket_open
            else "handshake_failed",
            "last_subscribe_error_type": None,
            "last_close_code": None,
            "last_close_exception_type": None,
            "first_frame_received": self._websocket_open,
            "last_payload_type": "prop" if self._websocket_open else None,
            "last_ignored_reason": None,
            "last_ignored_payload_type": None,
            "last_subscribe_sent_at": 122.0 if self._websocket_open else None,
            "last_message_at": 123.0 if self._websocket_open else None,
            "last_dispatched_at": 124.0 if self._websocket_open else None,
        }


class _TransportWithHealth:
    """Push transport double exposing aggregate health."""

    last_start_error_type: str | None = None
    last_runtime_error_type: str | None = None

    def __init__(self, *, websocket_open: bool = True) -> None:
        """Initialize transport health shape."""
        self._websocket_open = websocket_open
        if not websocket_open:
            self.last_runtime_error_type = "WSServerHandshakeError"

    @property
    def health(self) -> _TransportHealth:
        """Return aggregate-only transport health."""
        return _TransportHealth(websocket_open=self._websocket_open)

    async def async_start(self, _callback) -> None:
        """Start no-op transport."""

    async def async_stop(self) -> None:
        """Stop no-op transport."""


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_reports_client_capabilities(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """诊断能力边界必须明确区分已验证合同和未启用 live runtime."""
    coordinator = build_aggregate_runtime_coordinator()
    install_runtime_entry(
        hass,
        diagnostics_entry,
        coordinator,
        platforms=["light", "binary_sensor"],
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["client_capabilities"] == {
        "connection_mode": CONNECTION_MODE_CLOUD,
        "supported_connection_modes": ["cloud", "private", "lan"],
        "cloud_http_polling": False,
        "private_http_polling": False,
        "lan_direct_control": False,
        "scan_login_contract": True,
        "scan_login_runtime": False,
        "push_message_adapter": True,
        "runtime_payload_bridge": True,
        "websocket_message_contract": True,
        "websocket_transport_runtime": False,
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "push_connection": False,
        "websocket_subscription": False,
        "websocket_event_notifications": False,
        "local_gateway_control": False,
        "lan_control": False,
        "mqtt_subscription": False,
    }


@pytest.mark.asyncio
async def test_unloaded_diagnostics_does_not_report_live_runtime_capabilities(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """entry 未加载时只能报告静态合同，不能误报 active runtime 可用。"""
    hass.data[DOMAIN] = {}

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert data["runtime"]["loaded"] is False
    assert capabilities["connection_mode"] == CONNECTION_MODE_CLOUD
    assert capabilities["cloud_http_polling"] is False
    assert capabilities["private_http_polling"] is False
    assert capabilities["lan_direct_control"] is False
    assert capabilities["scan_login_runtime"] is False
    assert capabilities["websocket_transport_runtime"] is False
    assert capabilities["push_connection"] is False
    assert capabilities["websocket_subscription"] is False
    assert capabilities["websocket_event_notifications"] is False
    assert capabilities["local_gateway_control"] is False
    assert capabilities["lan_control"] is False
    assert capabilities["push_message_adapter"] is True
    assert capabilities["runtime_payload_bridge"] is True
    assert capabilities["mqtt_subscription"] is False


@pytest.mark.asyncio
async def test_diagnostics_derives_live_capabilities_from_runtime_managers(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """已加载 runtime 的 live 能力应来自实际 manager/client 是否存在。"""
    coordinator = build_aggregate_runtime_coordinator()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id].update(
        {
            "client": MagicMock(),
            "push_manager": SimpleNamespace(),
            "lan_runtime": SimpleNamespace(),
        }
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert capabilities["cloud_http_polling"] is True
    assert capabilities["scan_login_runtime"] is True
    assert capabilities["websocket_transport_runtime"] is True
    assert capabilities["push_connection"] is True
    assert capabilities["websocket_subscription"] is True
    assert capabilities["websocket_event_notifications"] is True
    assert capabilities["local_gateway_control"] is True
    assert capabilities["lan_control"] is True
    assert capabilities["mqtt_subscription"] is False


@pytest.mark.asyncio
async def test_diagnostics_does_not_treat_lan_start_failure_as_live_runtime(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """LAN 启动失败占位对象不能让 diagnostics 误报本地控制可用。"""
    coordinator = build_aggregate_runtime_coordinator()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["lan_runtime"] = (
        OptionalRuntimeStartupFailure(OSError("gateway-secret"))
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert capabilities["lan_direct_control"] is False
    assert capabilities["local_gateway_control"] is False
    assert capabilities["lan_control"] is False


@pytest.mark.asyncio
async def test_diagnostics_does_not_treat_stopped_push_manager_as_live_runtime(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """已停止的 push manager 不能让 diagnostics 误报 WebSocket 可用。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(coordinator, MagicMock())
    manager.health.running = False
    manager.health.started_count = 1
    manager.health.stopped_count = 1
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert data["runtime"]["health"]["push"] == _push_health(
        started_count=1,
        stopped_count=1,
    )
    assert capabilities["websocket_transport_runtime"] is False
    assert capabilities["push_connection"] is False
    assert capabilities["websocket_subscription"] is False
    assert capabilities["websocket_event_notifications"] is False


@pytest.mark.asyncio
async def test_diagnostics_does_not_treat_failed_stop_push_manager_as_live_runtime(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """stop 失败后的 push health 可见，但 active WebSocket 能力必须为 false。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(coordinator, MagicMock())
    manager.health.running = False
    manager.health.started_count = 1
    manager.health.last_error_type = "OSError"
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert data["runtime"]["health"]["push"] == _push_health(
        started_count=1,
        last_error_type="OSError",
    )
    assert capabilities["websocket_transport_runtime"] is False
    assert capabilities["push_connection"] is False
    assert capabilities["websocket_subscription"] is False
    assert capabilities["websocket_event_notifications"] is False


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
async def test_diagnostics_includes_push_transport_health(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """诊断应包含 WebSocket transport 聚合计数，便于排查事件通知延迟."""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(coordinator, _TransportWithHealth())
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"]["push"] == {
        **_push_health(running=True, started_count=1),
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
            "malformed_messages": 0,
            "control_frames": 1,
            "subscribe_sent_count": 1,
            "heartbeat_sent_count": 0,
            "pre_first_frame_abnormal_close_count": 0,
            "consecutive_pre_first_frame_abnormal_close_count": 0,
            "reconnect_pending": False,
            "reconnect_suspended": False,
            "next_reconnect_delay": None,
            "last_start_error_type": None,
            "last_runtime_error_type": None,
            "last_handshake_status": None,
            "last_disconnect_reason": None,
            "last_subscribe_error_type": None,
            "last_close_code": None,
            "last_close_exception_type": None,
            "first_frame_received": True,
            "last_payload_type": "prop",
            "last_ignored_reason": None,
            "last_ignored_payload_type": None,
            "last_subscribe_sent_at": 122.0,
            "last_message_at": 123.0,
            "last_dispatched_at": 124.0,
        },
    }

    await manager.async_stop()
