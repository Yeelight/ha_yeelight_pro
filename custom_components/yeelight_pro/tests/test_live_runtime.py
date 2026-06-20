"""Live WebSocket runtime wiring tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

from aiohttp import WSMsgType
import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_TYPE,
    CONF_ACCESS_TOKEN,
    DEVICE_EVENT_TYPE,
    CONF_LIVE_UPDATES,
    CONNECTION_MODE_LAN,
)
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.live_runtime import (
    async_start_live_runtime,
    live_updates_enabled,
)

from .config_entry_lifecycle_helpers import make_config_entry
from .push_transport_helpers import (
    FakeMessage,
    FakeSession,
    FakeWebSocket,
    OpenFakeWebSocket,
)


def _make_live_entry():
    """Build an entry without the lifecycle-test live-updates override."""
    entry = make_config_entry()
    entry.options = {}
    return entry


def test_live_updates_enabled_reads_entry_options() -> None:
    """云端/私有部署 live runtime 默认启用，并尊重显式关闭."""
    entry = _make_live_entry()

    assert live_updates_enabled(entry) is True

    entry.options = {CONF_LIVE_UPDATES: False}

    assert live_updates_enabled(entry) is False

    entry.options = {CONF_LIVE_UPDATES: True}

    assert live_updates_enabled(entry) is True


def test_live_updates_disabled_for_lan_only_entries() -> None:
    """LAN-only entry 没有云端 push token 订阅上下文，不能默认启动 WebSocket."""
    entry = _make_live_entry()
    entry.data["connection_mode"] = CONNECTION_MODE_LAN
    entry.options = {CONF_LIVE_UPDATES: True}

    assert live_updates_enabled(entry) is False


@pytest.mark.asyncio
async def test_live_runtime_starts_by_default_for_cloud_entries(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """默认云端配置应创建 WebSocket push manager."""
    entry = _make_live_entry()
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_create_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert session.connected_urls == ["wss://push.yeelight.com/ws/test_token"]

    await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_prefers_refreshed_runtime_token(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAuth 刷新后 WebSocket 应使用 coordinator/client 中的新 token."""
    entry = _make_live_entry()
    entry.data[CONF_ACCESS_TOKEN] = "old_entry_token"
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    coordinator = AsyncMock()
    coordinator.entry_data = {**entry.data, CONF_ACCESS_TOKEN: "fresh_runtime_token"}
    coordinator.client.access_token = "fresh_client_token"
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_create_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, coordinator)

    assert manager is not None
    assert session.connected_urls == ["wss://push.yeelight.com/ws/fresh_client_token"]

    await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_transport_token_provider_reads_latest_client_token(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """transport 每次新连接前应可读取 client 上的最新 access token."""
    entry = _make_live_entry()
    coordinator = AsyncMock()
    coordinator.entry_data = dict(entry.data)
    coordinator.client.access_token = "fresh-client-token"
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_create_clientsession",
        lambda _hass: FakeSession(OpenFakeWebSocket()),
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.YeelightPushWebSocketTransport",
        _capturing_transport_factory(captured),
    )

    manager = await async_start_live_runtime(hass, entry, coordinator)

    assert manager is not None
    token_provider = captured["token_provider"]
    assert callable(token_provider)
    assert token_provider() == "fresh-client-token"

    await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_starts_websocket_transport_when_enabled(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """启用 live_updates 后应启动真实 WebSocket transport seam."""
    entry = make_config_entry()
    entry.options = {CONF_LIVE_UPDATES: True}
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    coordinator = AsyncMock()
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_create_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, coordinator)

    assert manager is not None
    try:
        health = manager.health.as_dict()
        assert health["running"] is True
        assert health["started_count"] == 1
        assert health["stopped_count"] == 0
        assert health["handled_payloads"] == 0
        assert health["changed_payloads"] == 0
        assert health["unchanged_payloads"] == 0
        assert health["property_updates"] == 0
        assert health["applied_property_updates"] == 0
        assert health["unknown_property_updates"] == 0
        assert health["group_updates"] == 0
        assert health["topology_node_updates"] == 0
        assert health["dispatched_events"] == 0
        assert health["last_error_type"] is None
        assert health["last_payload_type"] is None
        assert health["last_payload_at"] is None
        transport_health = manager.transport_health
        assert transport_health is not None
        assert transport_health["running"] is True
        assert transport_health["websocket_open"] is True
        assert transport_health["connect_attempts"] == 1
        assert transport_health["connected_count"] == 1
        assert transport_health["received_messages"] == 0
        assert transport_health["first_frame_received"] is False
        assert transport_health["last_disconnect_reason"] is None
        assert session.connected_urls == ["wss://push.yeelight.com/ws/test_token"]
        assert websocket.sent_json[0]["method"] == "subscribe"
    finally:
        await manager.async_stop()

    assert websocket.closed is True


def _capturing_transport_factory(captured: dict[str, object]):
    """Return a fake transport class that records constructor kwargs."""

    class _Transport:
        last_start_error_type = None
        last_runtime_error_type = None

        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def async_start(self, callback):
            self._callback = callback

        async def async_stop(self):
            return None

    return _Transport


@pytest.mark.asyncio
async def test_live_runtime_recovers_after_initial_websocket_connect_failure(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """初始 WebSocket 网络失败应保持 runtime 存活并后台重连."""
    entry = make_config_entry()
    entry.options = {CONF_LIVE_UPDATES: True}
    websocket = OpenFakeWebSocket()
    session = FakeSession([OSError("token-secret"), websocket])
    coordinator = AsyncMock()
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_create_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, coordinator)

    assert manager is not None
    try:
        health = manager.health.as_dict()
        assert health["running"] is True
        assert health["started_count"] == 1
        assert health["stopped_count"] == 0
        assert health["handled_payloads"] == 0
        assert health["changed_payloads"] == 0
        assert health["unchanged_payloads"] == 0
        assert health["property_updates"] == 0
        assert health["applied_property_updates"] == 0
        assert health["unknown_property_updates"] == 0
        assert health["group_updates"] == 0
        assert health["topology_node_updates"] == 0
        assert health["dispatched_events"] == 0
        assert health["last_error_type"] == "OSError"
        assert health["last_payload_type"] is None
        assert health["last_payload_at"] is None
        transport_health = manager.transport_health
        assert transport_health is not None
        assert transport_health["running"] is True
        assert transport_health["websocket_open"] is False
        assert transport_health["connect_attempts"] == 1
        assert transport_health["connected_count"] == 0
        assert transport_health["received_messages"] == 0
        assert transport_health["first_frame_received"] is False
        assert transport_health["last_start_error_type"] == "OSError"
        assert transport_health["last_disconnect_reason"] == "connect_failed"
    finally:
        await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_routes_only_websocket_prop_and_event_to_coordinator(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WebSocket 事件通知只接受文档中的 prop/event 数据帧。"""
    entry = make_config_entry()
    entry.options = {CONF_LIVE_UPDATES: True}
    websocket = FakeWebSocket([
        FakeMessage(WSMsgType.TEXT, '{"method":"subscribe","code":"200"}'),
        FakeMessage(
            WSMsgType.TEXT,
            '{"type":"sse","nodes":[{"id":228215,"nt":2,"event":1}]}',
        ),
        FakeMessage(
            WSMsgType.TEXT,
            '{"type":"polling","nodes":[{"id":228215,"nt":2,"event":1}]}',
        ),
        FakeMessage(
            WSMsgType.TEXT,
            (
                '{"type":"prop","msgId":"message-1","nodes":['
                '{"id":228215,"nt":2,"params":{"p":false,"l":80}}'
                '],"timestamp":1724658984,"version":"1.0"}'
            ),
        ),
        FakeMessage(
            WSMsgType.TEXT,
            (
                '{"type":"event","msgId":"message-2","nodes":['
                '{"id":228215,"nt":2,"event":1}'
                '],"timestamp":1724658985,"version":"1.0"}'
            ),
        ),
        FakeMessage(
            WSMsgType.TEXT,
            '{"type":"server_sent","nodes":[{"id":228215,"nt":2,"event":1}]}',
        ),
    ])
    session = FakeSession(websocket)
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=AsyncMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228215: {
            "id": 228215,
            "device_id": 228215,
            "name": "WebSocket Scene Panel",
            "category": "scene_panel",
            "type": "event",
            "online": True,
            "params": {"p": True, "l": 25},
            "ha_product_model": {
                "components": [
                    {
                        "component_id": "scene_panel",
                        "category": "scene_panel",
                        "events": [{"event_id": 1, "name": "click"}],
                    }
                ],
            },
        }
    }
    coordinator.data = coordinator.devices
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_create_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, coordinator)
    await hass.async_block_till_done()

    assert manager is not None
    assert session.connected_urls == ["wss://push.yeelight.com/ws/test_token"]
    assert [message["method"] for message in websocket.sent_json] == ["subscribe"]
    assert manager.health.handled_payloads == 2
    device = coordinator.get_device(228215)
    assert device is not None
    assert device["params"]["p"] is False
    assert device["params"]["l"] == 80
    assert len(fired) == 1
    assert fired[0][ATTR_COMPONENT_ID] == "scene_panel"
    assert fired[0][ATTR_EVENT_TYPE] == "click"

    await manager.async_stop()
