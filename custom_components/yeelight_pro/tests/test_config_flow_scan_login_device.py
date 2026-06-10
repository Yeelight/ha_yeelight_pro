"""Scan-login device identifier tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.yeelight_pro.config_flow_scan_login_helpers import (
    async_scan_login_device_id,
)


@pytest.mark.asyncio
async def test_scan_login_device_id_hashes_ha_instance_id_without_leaking_raw_id(
    hass,
) -> None:
    """扫码 device 派生值应稳定且不暴露 HA 原始 instance id。"""
    raw_instance_id = "raw-instance-secret-123456"
    with patch(
        "custom_components.yeelight_pro.config_flow_scan_login_helpers."
        "instance_id.async_get",
        AsyncMock(return_value=raw_instance_id),
    ):
        first_device_id = await async_scan_login_device_id(hass)
        second_device_id = await async_scan_login_device_id(hass)

    assert first_device_id == second_device_id
    assert first_device_id.startswith("ha-")
    assert len(first_device_id) == 27
    int(first_device_id.removeprefix("ha-"), 16)
    assert raw_instance_id not in first_device_id
    assert "secret" not in first_device_id


@pytest.mark.asyncio
async def test_scan_login_device_id_changes_for_different_ha_instance_ids(
    hass,
) -> None:
    """不同 HA 实例应生成不同扫码 device，避免账号绑定冲突。"""
    with patch(
        "custom_components.yeelight_pro.config_flow_scan_login_helpers."
        "instance_id.async_get",
        AsyncMock(side_effect=["ha-instance-a", "ha-instance-b"]),
    ):
        first_device_id = await async_scan_login_device_id(hass)
        second_device_id = await async_scan_login_device_id(hass)

    assert first_device_id != second_device_id
    assert first_device_id.startswith("ha-")
    assert second_device_id.startswith("ha-")
