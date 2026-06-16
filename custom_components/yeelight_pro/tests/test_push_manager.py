"""Tests for the Yeelight Pro no-network push manager."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.push_manager import (
    PushPayloadCallback,
    PushManager,
)


class FakeTransport:
    """In-memory transport double used by PushManager tests."""

    def __init__(self) -> None:
        """Initialize the fake transport."""
        self.callback: PushPayloadCallback | None = None
        self.started_count = 0
        self.stopped_count = 0
        self.last_start_error_type: str | None = None
        self.last_runtime_error_type: str | None = None

    async def async_start(self, callback: PushPayloadCallback) -> None:
        """Store the callback without opening any network connection."""
        self.callback = callback
        self.started_count += 1

    async def async_stop(self) -> None:
        """Mark the fake transport as stopped."""
        self.stopped_count += 1

    async def emit(self, payload: Mapping[str, Any]) -> object | None:
        """Deliver a payload to the stored callback."""
        if self.callback is None:
            raise AssertionError("transport was not started")
        return await self.callback(payload)


@pytest.mark.asyncio
async def test_push_manager_start_stop_are_idempotent() -> None:
    """重复 start/stop 不应重复启动 transport."""
    coordinator = AsyncMock()
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    await manager.async_start()
    await manager.async_stop()
    await manager.async_stop()

    assert transport.started_count == 1
    assert transport.stopped_count == 1
    assert manager.health.as_dict() == {
        "running": False,
        "started_count": 1,
        "stopped_count": 1,
        "handled_payloads": 0,
        "last_error_type": None,
        "last_payload_type": None,
        "last_payload_at": None,
    }


@pytest.mark.asyncio
async def test_push_manager_forwards_payload_only_to_coordinator() -> None:
    """push payload 只进入 coordinator 的统一入口."""
    coordinator = AsyncMock()
    coordinator.async_handle_push_payload.return_value = ["event"]
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)
    payload = {"type": "prop", "nodes": [{"id": 228215, "params": {"p": True}}]}

    await manager.async_start()
    result = await transport.emit(payload)

    assert result == ["event"]
    coordinator.async_handle_push_payload.assert_awaited_once_with(payload)
    assert manager.health.handled_payloads == 1
    assert manager.health.last_error_type is None
    assert manager.health.last_payload_type == "prop"
    assert manager.health.last_payload_at is not None


@pytest.mark.asyncio
async def test_push_manager_accepts_payload_emitted_during_transport_start() -> None:
    """transport 启动阶段立即收到 payload 时不能因 running 时序被丢弃."""

    class ImmediateEmitTransport(FakeTransport):
        async def async_start(self, callback: PushPayloadCallback) -> None:
            await super().async_start(callback)
            await callback(
                {"type": "prop", "nodes": [{"id": 228216, "params": {"p": False}}]}
            )

    coordinator = AsyncMock()
    coordinator.async_handle_push_payload.return_value = ["state-update"]
    manager = PushManager(coordinator, ImmediateEmitTransport())

    await manager.async_start()

    coordinator.async_handle_push_payload.assert_awaited_once_with(
        {"type": "prop", "nodes": [{"id": 228216, "params": {"p": False}}]}
    )
    assert manager.health.as_dict() == {
        "running": True,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 1,
        "last_error_type": None,
        "last_payload_type": "prop",
        "last_payload_at": manager.health.last_payload_at,
    }
    assert manager.health.last_payload_at is not None


@pytest.mark.asyncio
async def test_push_manager_preserves_start_time_payload_error_type() -> None:
    """transport 启动阶段 payload 处理失败时应保留聚合错误类型."""

    class ImmediateEmitTransport(FakeTransport):
        async def async_start(self, callback: PushPayloadCallback) -> None:
            await super().async_start(callback)
            await callback({"type": "prop", "nodes": [{"id": "device-secret"}]})

    coordinator = AsyncMock()
    coordinator.async_handle_push_payload.side_effect = ValueError(
        "token-secret device-secret"
    )
    manager = PushManager(coordinator, ImmediateEmitTransport())

    await manager.async_start()

    assert manager.health.as_dict() == {
        "running": True,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": "ValueError",
        "last_payload_type": None,
        "last_payload_at": None,
    }
    assert "token-secret" not in str(manager.health.as_dict())
    assert "device-secret" not in str(manager.health.as_dict())


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
    assert manager.health.as_dict() == {
        "running": True,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": "RuntimeError",
        "last_payload_type": None,
        "last_payload_at": None,
    }
    assert "token-secret" not in str(manager.health.as_dict())
    assert "device-secret" not in str(manager.health.as_dict())


@pytest.mark.asyncio
async def test_push_manager_records_transport_start_error_type() -> None:
    """transport 启动失败只记录异常类型，并保持未运行."""

    class FailingStartTransport(FakeTransport):
        async def async_start(self, callback: PushPayloadCallback) -> None:
            raise ConnectionError("token-secret")

    manager = PushManager(AsyncMock(), FailingStartTransport())

    with pytest.raises(ConnectionError):
        await manager.async_start()

    assert manager.health.as_dict() == {
        "running": False,
        "started_count": 0,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": "ConnectionError",
        "last_payload_type": None,
        "last_payload_at": None,
    }


@pytest.mark.asyncio
async def test_push_manager_preserves_recoverable_start_error_type() -> None:
    """transport 后台重连时的启动错误应进入聚合 health."""

    class RecoveringStartTransport(FakeTransport):
        async def async_start(self, callback: PushPayloadCallback) -> None:
            await super().async_start(callback)
            self.last_start_error_type = "OSError"

    manager = PushManager(AsyncMock(), RecoveringStartTransport())

    await manager.async_start()

    assert manager.health.as_dict() == {
        "running": True,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": "OSError",
        "last_payload_type": None,
        "last_payload_at": None,
    }


@pytest.mark.asyncio
async def test_push_manager_reports_transport_runtime_error_type() -> None:
    """transport 后台错误应进入聚合 health，且不暴露异常文本."""
    coordinator = AsyncMock()
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    transport.last_runtime_error_type = "PushControlFrameError"

    assert manager.health.as_dict() == {
        "running": True,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": "PushControlFrameError",
        "last_payload_type": None,
        "last_payload_at": None,
    }
    assert "token-secret" not in str(manager.health.as_dict())


@pytest.mark.asyncio
async def test_push_manager_stop_failure_blocks_payloads_and_allows_retry() -> None:
    """transport stop 失败后不接收 payload，并允许后续 stop 重试清理."""

    class FailingStopTransport(FakeTransport):
        def __init__(self) -> None:
            super().__init__()
            self.fail_next_stop = True
            self.stop_attempts = 0

        async def async_stop(self) -> None:
            self.stop_attempts += 1
            if self.fail_next_stop:
                self.fail_next_stop = False
                raise OSError("token-secret device-secret")
            await super().async_stop()

    coordinator = AsyncMock()
    transport = FailingStopTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    with pytest.raises(OSError):
        await manager.async_stop()

    result = await transport.emit({"type": "prop", "nodes": [{"id": "device-secret"}]})

    assert result is None
    coordinator.async_handle_push_payload.assert_not_awaited()
    assert manager.health.as_dict() == {
        "running": False,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": "OSError",
        "last_payload_type": None,
        "last_payload_at": None,
    }
    assert "token-secret" not in str(manager.health.as_dict())
    assert "device-secret" not in str(manager.health.as_dict())

    await manager.async_stop()

    assert transport.stop_attempts == 2
    assert transport.stopped_count == 1
    assert manager.health.as_dict() == {
        "running": False,
        "started_count": 1,
        "stopped_count": 1,
        "handled_payloads": 0,
        "last_error_type": None,
        "last_payload_type": None,
        "last_payload_at": None,
    }
