"""Diagnostics redaction tests for Yeelight Pro."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_GATEWAYS,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_PRODUCT_IDS,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_GATEWAYS,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_PRODUCT_IDS,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_ROOMS,
    CONF_SCAN_LOGIN_DEVICE,
)
from custom_components.yeelight_pro.device_filter_options import (
    device_filter_form_keys,
)
from custom_components.yeelight_pro.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)

from .diagnostics_helpers import (
    build_diagnostics_entry,
    build_empty_diagnostics_coordinator,
    install_runtime_entry,
)


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


def test_diagnostics_redacts_device_filter_form_keys_by_contract() -> None:
    """设备过滤表单字段即使误入 diagnostics，也必须按敏感键处理."""
    assert set(device_filter_form_keys()).issubset(TO_REDACT)


@pytest.mark.asyncio
async def test_diagnostics_redacts_scan_login_device_identifier(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """扫码登录 device 即使是派生值，也不能进入 diagnostics 导出。"""
    diagnostics_entry.data[CONF_SCAN_LOGIN_DEVICE] = "ha-scan-device-secret"
    coordinator = build_empty_diagnostics_coordinator()
    install_runtime_entry(hass, diagnostics_entry, coordinator)

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    dumped = json.dumps(data, ensure_ascii=False)
    assert "ha-scan-device-secret" not in dumped
    assert data["config_entry"]["data"][CONF_SCAN_LOGIN_DEVICE] == "**REDACTED**"


@pytest.mark.asyncio
async def test_diagnostics_does_not_export_device_filter_form_values(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """设备过滤表单字段不能泄露 room/gateway/product/device 标识."""
    diagnostics_entry.options.update({
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_ROOMS: "room-secret-form",
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS: "room-secret-form-excluded",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_GATEWAYS: "gateway-secret-form",
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_GATEWAYS: "gateway-secret-form-excluded",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_PRODUCT_IDS: "product-secret-form",
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_PRODUCT_IDS: "product-secret-form-excluded",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: "device-secret-form",
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_DEVICES: "device-secret-form-excluded",
    })
    coordinator = build_empty_diagnostics_coordinator()
    install_runtime_entry(hass, diagnostics_entry, coordinator)

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    dumped = json.dumps(data, ensure_ascii=False)
    for secret in (
        "room-secret-form",
        "room-secret-form-excluded",
        "gateway-secret-form",
        "gateway-secret-form-excluded",
        "product-secret-form",
        "product-secret-form-excluded",
        "device-secret-form",
        "device-secret-form-excluded",
    ):
        assert secret not in dumped


@pytest.mark.asyncio
async def test_diagnostics_redacts_iot_registry_validation_error_details(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """registry 校验失败时 diagnostics 也只能暴露聚合，不导出错误细节."""
    monkeypatch.setattr(
        "custom_components.yeelight_pro.diagnostics.validate_iot_registry",
        lambda registry: [
            "duplicate category token-secret house 429392 device-secret-1 "
            "https://api.yeelight.com/apis/iot/house/429392"
        ],
    )
    coordinator = build_empty_diagnostics_coordinator()
    install_runtime_entry(hass, diagnostics_entry, coordinator)

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["iot_registry"]["valid"] is False
    assert data["runtime"]["iot_registry"]["error_count"] == 1
    assert "errors" not in data["runtime"]["iot_registry"]
    dumped = json.dumps(data, ensure_ascii=False)
    assert "duplicate category" not in dumped
    assert "token-secret" not in dumped
    assert "429392" not in dumped
    assert "device-secret-1" not in dumped
    assert "api.yeelight.com/apis/iot/house/429392" not in dumped


@pytest.mark.asyncio
async def test_diagnostics_whitelists_topology_diff_summary_fields(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """topology diff 诊断只接受固定聚合字段，忽略额外原始字段."""

    class UnsafeTopologySummary:
        def as_dict(self) -> dict[str, object]:
            return {
                "previous_generation": 1,
                "current_generation": 2,
                "added": {"devices": 1, "raw_ids": ["device-secret-1"]},
                "removed": {"devices": 0},
                "metadata_changed": {"rooms": 1},
                "total_added": 1,
                "total_removed": 0,
                "total_metadata_changed": 1,
                "total_changes": 2,
                "raw_device_id": "device-secret-1",
                "url": "https://api.yeelight.com/apis/iot/house/429392",
            }

    coordinator = build_empty_diagnostics_coordinator(
        topology_generation=2,
        topology_diff_summary=UnsafeTopologySummary(),
    )
    install_runtime_entry(hass, diagnostics_entry, coordinator)

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    summary = data["runtime"]["topology_diff_summary"]
    assert summary["added"] == {"devices": 1}
    assert summary["removed"] == {"devices": 0}
    assert summary["metadata_changed"] == {"rooms": 1}
    assert summary["total_changes"] == 2
    assert "raw_device_id" not in summary
    assert "url" not in summary
    dumped = json.dumps(data, ensure_ascii=False)
    assert "device-secret-1" not in dumped
    assert "api.yeelight.com/apis/iot/house/429392" not in dumped


@pytest.mark.asyncio
async def test_diagnostics_collapses_unknown_category_and_platform_values(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """category/type 聚合不能把上游异常原始字符串作为 key 输出."""
    coordinator = build_empty_diagnostics_coordinator()
    coordinator.devices = {
        1: {
            "category": "https://api.yeelight.com/apis/iot token-secret",
            "type": "house 429392 device-secret-1",
        }
    }
    install_runtime_entry(hass, diagnostics_entry, coordinator)

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["device_categories"] == {"unknown": 1}
    assert data["runtime"]["device_platforms"] == {"unknown": 1}
    dumped = json.dumps(data, ensure_ascii=False)
    assert "api.yeelight.com" not in dumped
    assert "token-secret" not in dumped
    assert "429392" not in dumped
    assert "device-secret-1" not in dumped
