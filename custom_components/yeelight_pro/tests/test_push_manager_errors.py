"""PushManager stop and error redaction tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.push_manager import PushManager

from .push_manager_helpers import FakeTransport, base_health


@pytest.mark.asyncio
async def test_push_manager_ignores_payload_after_stop() -> None:
    """stop 后 transport 延迟送达的 payload 不应再进入 coordinator."""
    coordinator = AsyncMock()
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    await manager.async_stop()
    result = await transport.emit({"type": "event", "nodes": []})

    assert result is None
    coordinator.async_handle_push_payload.assert_not_awaited()
    assert manager.health.handled_payloads == 0


@pytest.mark.asyncio
async def test_push_manager_records_error_type_without_payload_details() -> None:
    """coordinator 异常只进入聚合错误类型，不带原始 payload."""
    coordinator = AsyncMock()
    coordinator.async_handle_push_payload.side_effect = RuntimeError(
        "token-secret device-secret"
    )
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    result = await transport.emit(
        {"type": "prop", "nodes": [{"id": "device-secret", "params": {}}]}
    )

    assert result is None
    assert manager.health.as_dict() == base_health(
        running=True,
        started_count=1,
        last_error_type="RuntimeError",
    )
    assert "token-secret" not in str(manager.health.as_dict())
    assert "device-secret" not in str(manager.health.as_dict())
