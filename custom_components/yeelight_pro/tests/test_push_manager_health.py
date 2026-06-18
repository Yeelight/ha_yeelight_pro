"""PushManager transport health and error aggregation tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.push_manager import PushManager

from .push_manager_helpers import FakeTransport, FakeTransportHealth, base_health


@pytest.mark.asyncio
async def test_push_manager_records_transport_start_error_type() -> None:
    """transport 启动失败只记录异常类型，并保持未运行."""

    class FailingStartTransport(FakeTransport):
        async def async_start(self, callback) -> None:
            raise ConnectionError("token-secret")

    manager = PushManager(AsyncMock(), FailingStartTransport())

    with pytest.raises(ConnectionError):
        await manager.async_start()

    assert manager.health.as_dict() == base_health(last_error_type="ConnectionError")


@pytest.mark.asyncio
async def test_push_manager_preserves_recoverable_start_error_type() -> None:
    """transport 后台重连时的启动错误应进入聚合 health."""

    class RecoveringStartTransport(FakeTransport):
        async def async_start(self, callback) -> None:
            await super().async_start(callback)
            self.last_start_error_type = "OSError"

    manager = PushManager(AsyncMock(), RecoveringStartTransport())

    await manager.async_start()

    assert manager.health.as_dict() == base_health(
        running=True,
        started_count=1,
        last_error_type="OSError",
    )


@pytest.mark.asyncio
async def test_push_manager_reports_transport_runtime_error_type() -> None:
    """transport 后台错误应进入聚合 health，且不暴露异常文本."""
    coordinator = AsyncMock()
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    transport.last_runtime_error_type = "PushControlFrameError"

    assert manager.health.as_dict() == base_health(
        running=True,
        started_count=1,
        last_error_type="PushControlFrameError",
    )
    assert "token-secret" not in str(manager.health.as_dict())


@pytest.mark.asyncio
async def test_push_manager_exposes_transport_health_when_available() -> None:
    """manager diagnostics 应透出 transport 聚合 health，便于定位实时同步链路."""

    class TransportWithHealth(FakeTransport):
        @property
        def health(self) -> FakeTransportHealth:
            return FakeTransportHealth(
                {
                    "running": True,
                    "websocket_open": True,
                    "connect_attempts": 1,
                    "received_messages": 2,
                    "decoded_json_messages": 2,
                    "dispatched_payloads": 1,
                    "malformed_messages": 0,
                }
            )

    manager = PushManager(AsyncMock(), TransportWithHealth())

    await manager.async_start()

    assert manager.transport_health == {
        "running": True,
        "websocket_open": True,
        "connect_attempts": 1,
        "received_messages": 2,
        "decoded_json_messages": 2,
        "dispatched_payloads": 1,
        "malformed_messages": 0,
    }


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
    assert manager.health.as_dict() == base_health(
        started_count=1,
        last_error_type="OSError",
    )
    assert "token-secret" not in str(manager.health.as_dict())
    assert "device-secret" not in str(manager.health.as_dict())

    await manager.async_stop()

    assert transport.stop_attempts == 2
    assert transport.stopped_count == 1
    assert manager.health.as_dict() == base_health(started_count=1, stopped_count=1)
