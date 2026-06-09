"""Live WebSocket runtime wiring tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import CONF_LIVE_UPDATES
from custom_components.yeelight_pro.live_runtime import (
    async_start_live_runtime,
    live_updates_enabled,
)

from .config_entry_lifecycle_helpers import make_config_entry
from .push_transport_helpers import FakeSession, OpenFakeWebSocket


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
