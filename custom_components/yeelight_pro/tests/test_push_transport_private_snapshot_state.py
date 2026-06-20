"""Private subscribe snapshot state dispatch tests."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from aiohttp import WSMsgType
import pytest
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)
from custom_components.yeelight_pro.switch import YeelightProSwitch

from .push_transport_helpers import FakeMessage, FakeSession, FakeWebSocket


@pytest.mark.asyncio
async def test_private_subscribe_snapshot_state_dispatches_prop_payload() -> None:
    """私有订阅快照带状态字段时，不能只计入控制帧而不刷新实体."""
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"result":"ok","data":{"method":"subscribe","devices":['
                    '{"id":999998,"deviceId":228233,"nt":2,'
                    '"params":{"1-p":false,"2-p":true}},'
                    '{"id":999999,"deviceId":228234,"nt":2},'
                    '{"id":999997,"deviceId":228235,"nt":2,'
                    '"properties":[{"propId":"sp","index":1,"value":true}]}'
                    ']}}'
                ),
            )
        ]
    )
    callback = AsyncMock()
    transport = YeelightPushWebSocketTransport(
        session=FakeSession(websocket),
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(callback)
    await asyncio.sleep(0)

    callback.assert_awaited_once_with(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 999998,
                    "deviceId": 228233,
                    "nt": 2,
                    "params": {"1-p": False, "2-p": True},
                },
                {
                    "id": 999997,
                    "deviceId": 228235,
                    "nt": 2,
                    "properties": [{"propId": "sp", "index": 1, "value": True}],
                },
            ],
        }
    )
    health = transport.health.as_dict()
    assert health["control_frames"] == 1
    assert health["dispatched_payloads"] == 1
    assert health["last_subscribe_device_count"] == 3
    assert health["last_subscribe_state_device_count"] == 2
    assert health["last_payload_type"] == "prop"
    assert health["last_ignored_reason"] is None

    await transport.async_stop()


@pytest.mark.asyncio
async def test_private_subscribe_snapshot_state_refreshes_switch_entity(
    hass: HomeAssistant,
) -> None:
    """私有订阅快照状态应走完整 push 链路并即时刷新 HA 实体."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228233: {
            "id": 228233,
            "device_id": 228233,
            "name": "四键开关",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "params": {"1-p": True, "2-p": False},
        }
    }
    coordinator.data = coordinator.devices
    first_key = YeelightProSwitch(coordinator, 228233, component_id="switch_1")
    second_key = YeelightProSwitch(coordinator, 228233, component_id="switch_2")
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"result":"ok","data":{"method":"subscribe","devices":['
                    '{"id":999998,"deviceId":228233,"nt":2,'
                    '"params":{"1-p":false,"2-p":true}}'
                    ']}}'
                ),
            )
        ]
    )
    transport = YeelightPushWebSocketTransport(
        session=FakeSession(websocket),
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(coordinator.async_handle_push_payload)
    await asyncio.sleep(0)

    try:
        assert first_key.is_on is False
        assert second_key.is_on is True
        assert coordinator.last_push_property_summary.as_dict()["applied_device_updates"] == 1
        assert coordinator.last_push_property_summary.as_dict()["unknown_device_updates"] == 0
        assert transport.health.as_dict()["dispatched_payloads"] == 1
    finally:
        await transport.async_stop()
