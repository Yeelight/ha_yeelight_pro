"""Tests for the Yeelight Pro no-network push manager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.push_manager import (
    PushPayloadCallback,
    PushManager,
)
from custom_components.yeelight_pro.core.runtime_bridge import (
    RuntimePropertyUpdateSummary,
)
from .push_manager_helpers import FakeTransport, base_health


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
    assert manager.health.as_dict() == base_health(started_count=1, stopped_count=1)


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
async def test_push_manager_records_aggregate_payload_result() -> None:
    """push health 应暴露聚合处理结果，便于判断收到但未同步的原因。"""
    coordinator = AsyncMock()
    coordinator.last_push_property_summary = RuntimePropertyUpdateSummary(
        input_updates=3,
        applied_device_updates=1,
        unknown_device_updates=1,
        group_updates=0,
        topology_node_updates=1,
        unknown_node_samples=(
            {
                "node_id_hash": "safe-hash",
                "node_type": None,
                "param_keys": ["p"],
                "matched_collections": [],
                "reason": "not_loaded",
                "device_import_filter_enabled": False,
            },
        ),
        changed=True,
    )
    coordinator.async_handle_push_payload.return_value = ["event-1", "event-2"]
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    await transport.emit({"type": "prop", "nodes": [{"id": 1, "params": {"p": True}}]})

    assert manager.health.as_dict() == base_health(
        running=True,
        started_count=1,
        handled_payloads=1,
        changed_payloads=1,
        property_updates=3,
        applied_property_updates=1,
        unknown_property_updates=1,
        topology_node_updates=1,
        last_unknown_node_samples=[
            {
                "node_id_hash": "safe-hash",
                "node_type": None,
                "param_keys": ["p"],
                "matched_collections": [],
                "reason": "not_loaded",
                "device_import_filter_enabled": False,
            }
        ],
        dispatched_events=2,
        last_property_update_count=3,
        last_dispatched_event_count=2,
        last_payload_changed=True,
        last_payload_type="prop",
        last_payload_at=manager.health.last_payload_at,
    )
    assert manager.health.last_payload_at is not None


@pytest.mark.asyncio
async def test_push_manager_records_unchanged_payloads() -> None:
    """收到但未改变状态的推送应可诊断，避免实时链路问题变成黑盒。"""
    coordinator = AsyncMock()
    coordinator.last_push_property_summary = RuntimePropertyUpdateSummary(
        input_updates=0,
        changed=False,
    )
    coordinator.async_handle_push_payload.return_value = []
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    await transport.emit({"type": "prop", "nodes": []})

    assert manager.health.as_dict() == base_health(
        running=True,
        started_count=1,
        handled_payloads=1,
        unchanged_payloads=1,
        last_payload_type="prop",
        last_payload_at=manager.health.last_payload_at,
    )
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
    assert manager.health.as_dict() == base_health(
        running=True,
        started_count=1,
        handled_payloads=1,
        changed_payloads=1,
        dispatched_events=1,
        last_dispatched_event_count=1,
        last_payload_changed=True,
        last_payload_type="prop",
        last_payload_at=manager.health.last_payload_at,
    )
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

    assert manager.health.as_dict() == base_health(
        running=True,
        started_count=1,
        last_error_type="ValueError",
    )
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
    assert manager.health.as_dict() == base_health(
        running=True,
        started_count=1,
        last_error_type="RuntimeError",
    )
    assert "token-secret" not in str(manager.health.as_dict())
    assert "device-secret" not in str(manager.health.as_dict())
