"""Live WebSocket runtime wiring tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

from aiohttp import WSMsgType
import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_TYPE,
    DEVICE_EVENT_TYPE,
    CONF_LIVE_UPDATES,
)
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.live_runtime import (
    async_start_live_runtime,
    live_updates_enabled,
)

from .config_entry_lifecycle_helpers import make_config_entry
from .push_transport_helpers import FakeMessage, FakeSession, FakeWebSocket, OpenFakeWebSocket


def test_live_updates_enabled_reads_entry_options() -> None:
    """live runtime 只能由显式 options 开关启用."""
    entry = make_config_entry()

    assert live_updates_enabled(entry) is False

    entry.options = {CONF_LIVE_UPDATES: True}

    assert live_updates_enabled(entry) is True


@pytest.mark.asyncio
async def test_live_runtime_stays_disabled_by_default(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """默认配置不应创建 WebSocket session 或 push manager."""
    entry = make_config_entry()
    session = FakeSession(OpenFakeWebSocket())
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is None
    assert session.connected_urls == []


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
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, coordinator)

    assert manager is not None
    assert manager.health.as_dict() == {
        "running": True,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": None,
    }
    assert session.connected_urls == ["wss://push.yeelight.com/ws/test_token"]
    assert websocket.sent_json[0]["method"] == "subscribe"

    await manager.async_stop()

    assert websocket.closed is True


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
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, coordinator)

    assert manager is not None
    assert manager.health.as_dict() == {
        "running": True,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": "OSError",
    }

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
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
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
