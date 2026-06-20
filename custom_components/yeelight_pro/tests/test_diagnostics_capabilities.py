"""Diagnostics client capability boundary tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import CONNECTION_MODE_CLOUD, DOMAIN
from custom_components.yeelight_pro.diagnostics import async_get_config_entry_diagnostics
from custom_components.yeelight_pro.entry_setup import OptionalRuntimeStartupFailure
from custom_components.yeelight_pro.push_manager import PushManager

from .diagnostics_helpers import (
    build_aggregate_runtime_coordinator,
    build_diagnostics_entry,
    install_runtime_entry,
)
from .diagnostics_push_helpers import (
    _payload_flow,
    _push_health,
)










@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_reports_client_capabilities(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """诊断能力边界必须明确区分已验证合同和未启用 live runtime."""
    coordinator = build_aggregate_runtime_coordinator()
    install_runtime_entry(
        hass,
        diagnostics_entry,
        coordinator,
        platforms=["light", "binary_sensor"],
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["client_capabilities"] == {
        "connection_mode": CONNECTION_MODE_CLOUD,
        "supported_connection_modes": ["cloud", "private", "lan"],
        "cloud_http_polling": False,
        "private_http_polling": False,
        "lan_direct_control": False,
        "scan_login_contract": True,
        "scan_login_runtime": False,
        "push_message_adapter": True,
        "runtime_payload_bridge": True,
        "websocket_message_contract": True,
        "websocket_transport_runtime": False,
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "push_connection": False,
        "websocket_subscription": False,
        "websocket_event_notifications": False,
        "local_gateway_control": False,
        "lan_control": False,
        "mqtt_subscription": False,
    }


@pytest.mark.asyncio
async def test_unloaded_diagnostics_does_not_report_live_runtime_capabilities(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """entry 未加载时只能报告静态合同，不能误报 active runtime 可用。"""
    hass.data[DOMAIN] = {}

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert data["runtime"]["loaded"] is False
    assert capabilities["connection_mode"] == CONNECTION_MODE_CLOUD
    assert capabilities["cloud_http_polling"] is False
    assert capabilities["private_http_polling"] is False
    assert capabilities["lan_direct_control"] is False
    assert capabilities["scan_login_runtime"] is False
    assert capabilities["websocket_transport_runtime"] is False
    assert capabilities["push_connection"] is False
    assert capabilities["websocket_subscription"] is False
    assert capabilities["websocket_event_notifications"] is False
    assert capabilities["local_gateway_control"] is False
    assert capabilities["lan_control"] is False
    assert capabilities["push_message_adapter"] is True
    assert capabilities["runtime_payload_bridge"] is True
    assert capabilities["mqtt_subscription"] is False


@pytest.mark.asyncio
async def test_diagnostics_derives_live_capabilities_from_runtime_managers(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """已加载 runtime 的 live 能力应来自实际 manager/client 是否存在。"""
    coordinator = build_aggregate_runtime_coordinator()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id].update(
        {
            "client": MagicMock(),
            "push_manager": SimpleNamespace(),
            "lan_runtime": SimpleNamespace(),
        }
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert capabilities["cloud_http_polling"] is True
    assert capabilities["scan_login_runtime"] is True
    assert capabilities["websocket_transport_runtime"] is True
    assert capabilities["push_connection"] is True
    assert capabilities["websocket_subscription"] is True
    assert capabilities["websocket_event_notifications"] is True
    assert capabilities["local_gateway_control"] is True
    assert capabilities["lan_control"] is True
    assert capabilities["mqtt_subscription"] is False


@pytest.mark.asyncio
async def test_diagnostics_does_not_treat_lan_start_failure_as_live_runtime(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """LAN 启动失败占位对象不能让 diagnostics 误报本地控制可用。"""
    coordinator = build_aggregate_runtime_coordinator()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["lan_runtime"] = (
        OptionalRuntimeStartupFailure(OSError("gateway-secret"))
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert capabilities["lan_direct_control"] is False
    assert capabilities["local_gateway_control"] is False
    assert capabilities["lan_control"] is False


@pytest.mark.asyncio
async def test_diagnostics_does_not_treat_stopped_push_manager_as_live_runtime(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """已停止的 push manager 不能让 diagnostics 误报 WebSocket 可用。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(coordinator, MagicMock())
    manager.health.running = False
    manager.health.started_count = 1
    manager.health.stopped_count = 1
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert data["runtime"]["health"]["push"] == _push_health(
        started_count=1,
        stopped_count=1,
        payload_flow=_payload_flow(
            status="not_running",
            transport_health_available=False,
            import_filter_active=True,
        ),
    )
    assert capabilities["websocket_transport_runtime"] is False
    assert capabilities["push_connection"] is False
    assert capabilities["websocket_subscription"] is False
    assert capabilities["websocket_event_notifications"] is False


@pytest.mark.asyncio
async def test_diagnostics_does_not_treat_failed_stop_push_manager_as_live_runtime(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """stop 失败后的 push health 可见，但 active WebSocket 能力必须为 false。"""
    coordinator = build_aggregate_runtime_coordinator()
    manager = PushManager(coordinator, MagicMock())
    manager.health.running = False
    manager.health.started_count = 1
    manager.health.last_error_type = "OSError"
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["push_manager"] = manager

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)
    capabilities = data["runtime"]["client_capabilities"]

    assert data["runtime"]["health"]["push"] == _push_health(
        started_count=1,
        last_error_type="OSError",
        payload_flow=_payload_flow(
            status="not_running",
            transport_health_available=False,
            import_filter_active=True,
        ),
    )
    assert capabilities["websocket_transport_runtime"] is False
    assert capabilities["push_connection"] is False
    assert capabilities["websocket_subscription"] is False
    assert capabilities["websocket_event_notifications"] is False
