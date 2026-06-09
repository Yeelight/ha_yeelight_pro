"""Coordinator error-redaction regression tests."""
from __future__ import annotations

import traceback
from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    ConnectionError,
    DeviceNotFoundError,
)

from .coordinator_helpers import _client_with_payloads


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint_name", "base_devices"),
    [
        pytest.param("get_devices", [], id="devices"),
        pytest.param(
            "get_areas",
            [[{"id": 1, "name": "Lamp", "category": "light", "pid": 100}]],
            id="auxiliary-auth",
        ),
    ],
)
async def test_refresh_auth_failure_traceback_drops_sensitive_cause(
    hass: HomeAssistant,
    endpoint_name: str,
    base_devices: list[list[dict]],
) -> None:
    """刷新认证失败的 HA traceback 不应保留下游敏感异常链."""
    auth_error = AuthenticationError(
        "token=secret-token https://api.yeelight.com house=12345 device=67890"
    )
    client = _client_with_payloads(devices=base_devices)
    setattr(client, endpoint_name, AsyncMock(side_effect=auth_error))
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    with pytest.raises(ConfigEntryAuthFailed) as exc_info:
        await coordinator._async_update_data()

    assert str(exc_info.value) == "Yeelight Pro authentication failed"
    assert exc_info.value.__cause__ is None
    formatted = "".join(
        traceback.format_exception(
            type(exc_info.value),
            exc_info.value,
            exc_info.value.__traceback__,
        )
    )
    assert "secret-token" not in formatted
    assert "api.yeelight.com" not in formatted
    assert "12345" not in formatted
    assert "67890" not in formatted


@pytest.mark.asyncio
async def test_update_failure_redacts_nested_error_details(
    hass: HomeAssistant,
    caplog,
) -> None:
    """主刷新失败的日志和 UpdateFailed 信息只暴露异常类型."""
    client = _client_with_payloads(devices=[])
    client.get_devices.side_effect = ConnectionError(
        "house 12345 token secret-token https://api.yeelight.com device 67890"
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    with caplog.at_level("ERROR"), pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()

    assert str(exc_info.value) == "Connection error: ConnectionError"
    assert (
        "Connection error while updating Yeelight Pro data: ConnectionError"
        in caplog.text
    )
    assert "secret-token" not in caplog.text
    assert "api.yeelight.com" not in caplog.text
    assert "12345" not in caplog.text
    assert "67890" not in caplog.text


@pytest.mark.asyncio
async def test_update_failure_traceback_does_not_keep_sensitive_cause(
    hass: HomeAssistant,
) -> None:
    """UpdateFailed traceback 不应保留下游敏感异常链."""
    client = _client_with_payloads(devices=[])
    client.get_devices.side_effect = ConnectionError(
        "house 12345 token secret-token https://api.yeelight.com device 67890"
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()

    assert exc_info.value.__cause__ is None
    formatted = "".join(
        traceback.format_exception(
            type(exc_info.value),
            exc_info.value,
            exc_info.value.__traceback__,
        )
    )
    assert "secret-token" not in formatted
    assert "api.yeelight.com" not in formatted
    assert "12345" not in formatted
    assert "67890" not in formatted


@pytest.mark.asyncio
async def test_control_missing_device_error_does_not_include_device_id(
    hass: HomeAssistant,
) -> None:
    """缺失设备错误不能把 Yeelight device_id 暴露到异常消息."""
    client = AsyncMock(spec=YeelightProClient)
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)
    coordinator.devices = {}

    with pytest.raises(DeviceNotFoundError) as exc_info:
        await coordinator.async_control_device(67890, {"p": True})

    assert str(exc_info.value) == "Device not found"
    assert "67890" not in str(exc_info.value)
