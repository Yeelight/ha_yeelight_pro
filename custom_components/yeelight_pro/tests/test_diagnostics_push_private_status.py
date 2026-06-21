"""Diagnostics private push status boundary tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.diagnostics import async_get_config_entry_diagnostics
from custom_components.yeelight_pro.push_manager import PushManager

from .diagnostics_helpers import (
    build_aggregate_runtime_coordinator,
    build_diagnostics_entry,
    install_runtime_entry,
)
from .diagnostics_push_helpers import _payload_flow, _TransportWithHealth


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_reports_private_status_non_success_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """私有 push 返回非成功状态且无业务帧时，应区别于节点匹配失败。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=0,
            private_status_non_success_frames=1,
        ),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    push = data["runtime"]["health"]["push"]
    assert push["push_sync_status"] == "private_status_non_success"
    assert push["payload_flow"] == _payload_flow(
        status="private_status_non_success",
        private_status_non_success_count=1,
        data_topology_check="not_applicable_no_data_payload",
        import_filter_active=True,
    )
    assert push["transport"]["last_private_status_result"] == "non_success"
    assert push["transport"]["last_private_status_reason"] is None
    assert push["transport"]["private_status_non_success_frames"] == 1

    await manager.async_stop()


@pytest.mark.asyncio
async def test_diagnostics_reports_no_subscribable_devices_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """私有 push 明确没有可订阅设备时，应区别于 HA 拓扑/过滤问题。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=0,
            private_status_non_success_frames=1,
            private_status_reason="no_subscribable_devices",
        ),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    push = data["runtime"]["health"]["push"]
    assert push["push_sync_status"] == "private_push_no_subscribable_devices"
    assert push["payload_flow"] == _payload_flow(
        status="private_push_no_subscribable_devices",
        private_status_non_success_count=1,
        private_status_reason="no_subscribable_devices",
        data_topology_check="not_applicable_no_data_payload",
        import_filter_active=True,
    )
    assert push["transport"]["last_private_status_reason"] == (
        "no_subscribable_devices"
    )

    await manager.async_stop()


@pytest.mark.asyncio
async def test_diagnostics_reports_unsupported_payload_received_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """收到未识别 JSON 帧时，应和完全没有业务帧区分开。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(dispatched_payloads=0, unsupported_messages=2),
    )
    await manager.async_start()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    push = data["runtime"]["health"]["push"]
    assert push["push_sync_status"] == "unsupported_payload_received"
    assert push["payload_flow"] == _payload_flow(
        status="unsupported_payload_received",
        unsupported_payload_count=2,
        data_topology_check="not_applicable_no_data_payload",
        import_filter_active=True,
    )
    assert push["transport"]["unsupported_messages"] == 2

    await manager.async_stop()
