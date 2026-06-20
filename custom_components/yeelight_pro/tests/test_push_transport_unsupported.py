"""Unsupported payload diagnostics tests for Yeelight push transport."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from aiohttp import WSMsgType
import pytest

from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)

from .push_transport_helpers import FakeMessage, FakeSession, FakeWebSocket


@pytest.mark.asyncio
async def test_push_transport_records_unsupported_payload_shape_without_values() -> None:
    """未识别 JSON 只记录字段 shape，不能把 payload 值带进 diagnostics."""
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"method":"message","payloadSecret":"secret-value",'
                    '"data":{"payloadSecret":"nested-secret",'
                    '"payload":[{"deviceId":"device-secret"}]}}'
                ),
            )
        ]
    )
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    assert health["dispatched_payloads"] == 0
    assert health["unsupported_messages"] == 1
    assert health["last_ignored_reason"] == "unsupported_payload"
    assert health["last_unsupported_payload_shape"] == {
        "objects": [
            {
                "path": "root",
                "keys": ["data", "method", "payloadSecret"],
                "flags": {
                    "type": False,
                    "method": True,
                    "nodes": False,
                    "data": True,
                    "params": False,
                    "result": False,
                },
            },
            {
                "path": "root.data",
                "keys": ["payload", "payloadSecret"],
                "flags": {
                    "type": False,
                    "method": False,
                    "nodes": False,
                    "data": False,
                    "params": False,
                    "result": False,
                },
            },
        ],
        "status": None,
    }
    assert "secret-value" not in str(health)
    assert "device-secret" not in str(health)

    await transport.async_stop()
