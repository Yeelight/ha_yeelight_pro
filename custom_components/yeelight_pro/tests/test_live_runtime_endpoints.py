"""Endpoint selection tests for Yeelight Pro live WebSocket runtime."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_CLOUD_REGION,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
)
from custom_components.yeelight_pro.live_runtime import async_start_live_runtime

from .config_entry_lifecycle_helpers import make_config_entry
from .push_transport_helpers import FakeSession, OpenFakeWebSocket


def _make_live_entry():
    """Build an entry without the lifecycle-test live-updates override."""
    entry = make_config_entry()
    entry.options = {}
    return entry


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
async def test_live_runtime_does_not_override_private_push_heartbeat(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """私有部署 runtime 不应偏离开放平台文档建议的 20 秒心跳."""
    entry = _make_live_entry()
    entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_PRIVATE
    entry.data[CONF_PRIVATE_DOMAIN] = "http://api-test.yeedev.com"
    entry.data[CONF_PRIVATE_PUSH_DOMAIN] = "ws://ws-test.yeedev.com/ws"
    session = FakeSession(OpenFakeWebSocket())
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.YeelightPushWebSocketTransport",
        _capturing_transport_factory(captured),
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert "heartbeat_interval_seconds" not in captured

    await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_enables_private_fake_ip_detection_without_proxy(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """私有部署可检测 fake-ip DNS，但不猜测宿主机代理端口。"""
    entry = _make_live_entry()
    entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_PRIVATE
    entry.data[CONF_PRIVATE_DOMAIN] = "http://api-test.yeedev.com"
    entry.data[CONF_PRIVATE_PUSH_DOMAIN] = "ws://ws-test.yeedev.com/ws"
    session = FakeSession(OpenFakeWebSocket())
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.YeelightPushWebSocketTransport",
        _capturing_transport_factory(captured),
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert "proxy" not in captured or captured["proxy"] is None
    assert "auto_proxy_candidates" not in captured
    assert captured["enable_ip_fallback"] is True

    await manager.async_stop()


@pytest.mark.asyncio
async def test_live_runtime_keeps_documented_cloud_push_heartbeat(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """云端 push runtime 继续使用文档建议的 20 秒心跳."""
    entry = _make_live_entry()
    entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_CLOUD
    session = FakeSession(OpenFakeWebSocket())
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.async_get_clientsession",
        lambda _hass: session,
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.live_runtime.YeelightPushWebSocketTransport",
        _capturing_transport_factory(captured),
    )

    manager = await async_start_live_runtime(hass, entry, AsyncMock())

    assert manager is not None
    assert "heartbeat_interval_seconds" not in captured

    await manager.async_stop()


def _capturing_transport_factory(captured: dict[str, object]):
    """Return a fake transport class that records constructor heartbeat args."""

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
