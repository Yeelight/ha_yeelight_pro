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
    CONF_CONNECTION_MODE,
    CONF_CLOUD_REGION,
    CONF_LIVE_UPDATES,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
    CONNECTION_MODE_PRIVATE,
)
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.live_runtime import (
    async_start_live_runtime,
    live_updates_enabled,
)

from .config_entry_lifecycle_helpers import make_config_entry
from .push_transport_helpers import FakeMessage, FakeSession, FakeWebSocket, OpenFakeWebSocket


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
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert session.connected_urls == ["wss://push.yeelight.com/ws/test_token"]

    await manager.async_stop()


@pytest.mark.parametrize(
    ("region", "expected_url"),
    [
        ("sg", "wss://push-sg.yeelight.com/ws/test_token"),
        ("us", "wss://push-us.yeelight.com/ws/test_token"),
        ("de", "wss://push-de.yeelight.com/ws/test_token"),
    ],
)
@pytest.mark.asyncio
async def test_live_runtime_uses_region_push_endpoint_for_cloud_entries(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    region: str,
    expected_url: str,
) -> None:
    """不同云端区域应连接各自的 WebSocket push endpoint."""
    entry = _make_live_entry()
    entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_CLOUD
    entry.data[CONF_CLOUD_REGION] = region
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert session.connected_urls == [expected_url]

    await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_uses_private_deployment_push_endpoint(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """私有部署实时通知应优先连接用户填写的 WebSocket endpoint."""
    entry = _make_live_entry()
    entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_PRIVATE
    entry.data[CONF_PRIVATE_DOMAIN] = "https://api-dev.yeedev.com"
    entry.data[CONF_PRIVATE_PUSH_DOMAIN] = "ws-dev.yeedev.com"
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert session.connected_urls == ["wss://ws-dev.yeedev.com/ws/test_token"]

    await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_falls_back_to_private_api_host_for_legacy_entries(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧私有 entry 缺少 push URL 时才从 API host 派生兼容 endpoint."""
    entry = _make_live_entry()
    entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_PRIVATE
    entry.data[CONF_PRIVATE_DOMAIN] = "https://api-dev.yeedev.com"
    entry.data[CONF_PRIVATE_PUSH_DOMAIN] = ""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert session.connected_urls == ["wss://api-dev.yeedev.com/ws/test_token"]

    await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_falls_back_to_private_test_push_host(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """api-test.yeedev.com currently uses the separate ws-test push endpoint."""
    entry = _make_live_entry()
    entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_PRIVATE
    entry.data[CONF_PRIVATE_DOMAIN] = "http://api-test.yeedev.com"
    entry.data[CONF_PRIVATE_PUSH_DOMAIN] = ""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert session.connected_urls == ["ws://ws-test.yeedev.com/ws/test_token"]

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
        "last_payload_type": None,
        "last_payload_at": None,
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
        "last_payload_type": None,
        "last_payload_at": None,
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
