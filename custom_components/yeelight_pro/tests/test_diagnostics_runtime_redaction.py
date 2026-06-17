"""Runtime diagnostics redaction tests for Yeelight Pro."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.analytics_coordinator import AnalyticsSnapshot
from custom_components.yeelight_pro.diagnostics import async_get_config_entry_diagnostics
from custom_components.yeelight_pro.entry_setup import OptionalRuntimeStartupFailure
from .diagnostics_helpers import (
    build_diagnostics_entry,
    build_empty_diagnostics_coordinator,
    install_runtime_entry,
)


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_reports_safe_property_hydration_aggregates(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """补水诊断只暴露聚合计数，不导出设备 id、属性名或属性值."""
    coordinator = build_empty_diagnostics_coordinator()
    coordinator.property_hydration_diagnostics = {
        "request_groups": 1,
        "requested_devices": 3,
        "requested_property_sets": 37,
        "requested_node_properties": 111,
        "response_devices": 2,
        "response_values": 5,
        "merged_devices": 2,
        "merged_values": 5,
        "empty_response_groups": 0,
        "failed_groups": 1,
        "raw_device_id": "311930423",
    }
    install_runtime_entry(hass, diagnostics_entry, coordinator)

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["property_hydration"] == {
        "request_groups": 1,
        "requested_devices": 3,
        "requested_property_sets": 37,
        "requested_node_properties": 111,
        "response_devices": 2,
        "response_values": 5,
        "merged_devices": 2,
        "merged_values": 5,
        "empty_response_groups": 0,
        "failed_groups": 1,
    }
    dumped = json.dumps(data, ensure_ascii=False)
    assert "311930423" not in dumped

@pytest.mark.asyncio
async def test_diagnostics_reports_safe_runtime_health(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """运行时健康诊断只能暴露安全状态，不导出异常消息."""
    coordinator = build_empty_diagnostics_coordinator(
        last_update_success=False,
        last_exception=RuntimeError(
            "failed https://api.yeelight.com/apis/iot/house/429392 token-secret"
        ),
    )
    install_runtime_entry(
        hass,
        diagnostics_entry,
        coordinator,
        platforms=[
            "binary_sensor",
            "button",
            "climate",
            "cover",
            "event",
            "fan",
            "light",
            "number",
            "select",
            "sensor",
            "switch",
        ],
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"] == {
        "last_update_success": False,
        "last_exception_type": "RuntimeError",
        "loaded_platform_count": 11,
        "expected_platform_count": 11,
        "platforms_match_options": True,
        "live_updates_intended": True,
        "live_updates_active": False,
        "polling_fallback_active": False,
        "polling_fallback_interval_seconds": None,
        "push": None,
        "lan": None,
    }
    assert data["runtime"]["analytics"] == {
        "enabled": False,
        "last_update_success": None,
        "last_exception_type": None,
        "has_snapshot": False,
        "endpoint_count": 0,
        "successful_endpoint_count": 0,
    }
    dumped = json.dumps(data, ensure_ascii=False)
    assert "RuntimeError" in dumped
    assert "api.yeelight.com/apis/iot/house/429392" not in dumped
    assert "token-secret" not in dumped


@pytest.mark.asyncio
async def test_diagnostics_reports_analytics_soft_failure_without_details(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """analytics 初次失败只暴露聚合状态，不导出 HTTP 细节。"""
    coordinator = build_empty_diagnostics_coordinator()
    analytics_coordinator = MagicMock()
    analytics_coordinator.last_update_success = False
    analytics_coordinator.last_exception = UpdateFailed(
        "Failed https://api.yeelight.com/apis/iot/house/429392 token-secret"
    )
    analytics_coordinator.data = None
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["sensor"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["analytics_coordinator"] = (
        analytics_coordinator
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["analytics"] == {
        "enabled": True,
        "last_update_success": False,
        "last_exception_type": "UpdateFailed",
        "has_snapshot": False,
        "endpoint_count": 0,
        "successful_endpoint_count": 0,
        "endpoint_errors": {},
    }
    dumped = json.dumps(data, ensure_ascii=False)
    assert "UpdateFailed" in dumped
    assert "api.yeelight.com/apis/iot/house/429392" not in dumped
    assert "token-secret" not in dumped


@pytest.mark.asyncio
async def test_diagnostics_reports_analytics_endpoint_errors_without_details(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """analytics 部分失败时只暴露 endpoint 和错误类型，不导出原始响应."""
    coordinator = build_empty_diagnostics_coordinator()
    analytics_coordinator = MagicMock()
    analytics_coordinator.last_update_success = True
    analytics_coordinator.last_exception = None
    analytics_coordinator.data = AnalyticsSnapshot(
        date_code="2024-08",
        day_code="2024-08-08",
        trend_start_date="2024-08-02",
        trend_end_date="2024-08-08",
        endpoint_errors={
            "alarm_trend": "ConnectionError",
            "energy_trend": "InvalidResponse",
        },
    )
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["sensor"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["analytics_coordinator"] = (
        analytics_coordinator
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["analytics"] == {
        "enabled": True,
        "last_update_success": True,
        "last_exception_type": None,
        "has_snapshot": True,
        "endpoint_count": 0,
        "successful_endpoint_count": 0,
        "endpoint_errors": {
            "alarm_trend": "ConnectionError",
            "energy_trend": "InvalidResponse",
        },
    }
    dumped = json.dumps(data, ensure_ascii=False)
    assert "alarm_trend" in dumped
    assert "energy_trend" in dumped
    assert "api.yeelight.com/apis/iot/house/429392" not in dumped
    assert "token-secret" not in dumped


@pytest.mark.asyncio
async def test_diagnostics_reports_optional_lan_start_failure_without_details(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """LAN 可选启动失败只暴露聚合错误类型，不导出 host/token/原始消息."""
    coordinator = build_empty_diagnostics_coordinator()
    install_runtime_entry(hass, diagnostics_entry, coordinator, platforms=["light"])
    hass.data[DOMAIN][diagnostics_entry.entry_id]["lan_runtime"] = (
        OptionalRuntimeStartupFailure(
            OSError("192.168.1.20 token=secret gateway-secret")
        )
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["health"]["lan"] == {
        "running": False,
        "connected": False,
        "sent_count": 0,
        "received_count": 0,
        "last_error_type": "OSError",
    }
    dumped = json.dumps(data, ensure_ascii=False)
    assert "192.168.1.20" not in dumped
    assert "secret" not in dumped
    assert "gateway-secret" not in dumped
