"""Diagnostics push data-payload status tests."""
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
async def test_diagnostics_reports_data_payload_not_in_topology_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """业务帧节点样本未命中当前拓扑时，应明确暴露聚合状态。"""
    coordinator = build_aggregate_runtime_coordinator()
    coordinator.last_push_property_summary = {
        "input_updates": 1,
        "unknown_device_updates": 1,
        "changed": False,
    }
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=1,
            recent_data_nodes_matching_loaded_topology=0,
            recent_data_nodes_not_loaded=1,
            data_node_hash="a5fe26f5cfedbc8c",
        ),
    )
    await manager.async_start()
    manager.health.handled_payloads = 1
    manager.health.unknown_property_updates = 1
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"]["push"]["push_sync_status"] == (
        "data_payload_not_in_topology"
    )
    assert data["runtime"]["health"]["push"]["payload_flow"] == _payload_flow(
        status="data_payload_not_in_topology",
        data_payload_received=True,
        data_payload_count=1,
        handled_payload_count=1,
        last_data_nodes_not_loaded=1,
        recent_data_nodes_not_loaded=1,
        data_topology_check="not_in_loaded_topology",
        data_import_filter_check="unknown_or_unloaded_nodes_may_be_filtered",
        import_filter_active=True,
    )

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_data_payload_routed_no_state_change_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """业务帧命中拓扑但值相同时，应和节点未命中区分开。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=1,
            recent_data_nodes_matching_loaded_topology=1,
            recent_data_nodes_not_loaded=0,
        ),
    )
    await manager.async_start()
    manager.health.handled_payloads = 1
    manager.health.property_updates = 1
    manager.health.routed_property_updates = 1
    manager.health.last_payload_changed = False
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"]["push"]["push_sync_status"] == (
        "data_payload_routed_no_state_change"
    )
    assert data["runtime"]["health"]["push"]["payload_flow"] == _payload_flow(
        status="data_payload_routed_no_state_change",
        data_payload_received=True,
        data_payload_count=1,
        handled_payload_count=1,
        property_update_count=1,
        last_data_nodes_matching_loaded_topology=1,
        recent_data_nodes_matching_loaded_topology=1,
        data_topology_check="matched_loaded_topology",
        data_import_filter_check="no_filter_related_miss_detected",
        import_filter_active=True,
    )

    await manager.async_stop()

@pytest.mark.asyncio
async def test_diagnostics_reports_data_payload_empty_params_status(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """业务帧节点存在但没有可合并属性时，应暴露为空参数状态。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=1,
            recent_data_nodes_matching_loaded_topology=1,
            recent_data_nodes_not_loaded=0,
        ),
    )
    await manager.async_start()
    manager.health.handled_payloads = 1
    manager.health.property_updates = 1
    manager.health.empty_param_updates = 1
    manager.health.last_payload_changed = False
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"]["push"]["push_sync_status"] == (
        "data_payload_empty_params"
    )
    assert data["runtime"]["health"]["push"]["payload_flow"] == _payload_flow(
        status="data_payload_empty_params",
        data_payload_received=True,
        data_payload_count=1,
        handled_payload_count=1,
        property_update_count=1,
        last_data_nodes_matching_loaded_topology=1,
        recent_data_nodes_matching_loaded_topology=1,
        data_topology_check="matched_loaded_topology",
        data_import_filter_check="no_filter_related_miss_detected",
        import_filter_active=True,
    )

    await manager.async_stop()


@pytest.mark.asyncio
async def test_diagnostics_reports_push_payload_apply_and_listener_timing(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """业务帧诊断应暴露处理耗时和 HA listener 命中数。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(
        coordinator,
        _TransportWithHealth(
            dispatched_payloads=1,
            recent_data_nodes_matching_loaded_topology=1,
            recent_data_nodes_not_loaded=0,
        ),
    )
    await manager.async_start()
    manager.health.handled_payloads = 1
    manager.health.property_updates = 1
    manager.health.routed_property_updates = 1
    manager.health.last_payload_changed = True
    manager.health.last_payload_handle_duration_ms = 3.5
    manager.health.last_listener_notification_count = 2
    manager.health.last_listener_context_count = 1
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"]["push"]["payload_flow"] == _payload_flow(
        status="data_payload_applied",
        data_payload_received=True,
        data_payload_count=1,
        handled_payload_count=1,
        property_update_count=1,
        last_payload_handle_duration_ms=3.5,
        last_listener_notification_count=2,
        last_listener_context_count=1,
        last_data_nodes_matching_loaded_topology=1,
        recent_data_nodes_matching_loaded_topology=1,
        data_topology_check="matched_loaded_topology",
        data_import_filter_check="no_filter_related_miss_detected",
        import_filter_active=True,
    )

    await manager.async_stop()
