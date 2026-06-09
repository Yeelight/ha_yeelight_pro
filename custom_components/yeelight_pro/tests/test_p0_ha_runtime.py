"""P0 Home Assistant runtime auth/control regression tests."""
from __future__ import annotations

import importlib
import traceback
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from custom_components.yeelight_pro.const import DOMAIN, PLATFORMS
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    ConnectionError as YeelightConnectionError,
    TokenExpiredError,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_error",
    [
        pytest.param(TokenExpiredError("expired"), id="401-token-expired"),
        pytest.param(AuthenticationError("forbidden"), id="403-forbidden"),
    ],
)
async def test_setup_entry_auth_failure_raises_config_entry_auth_failed(
    hass: HomeAssistant,
    mock_config_entry,
    auth_error: AuthenticationError,
) -> None:
    """setup 阶段 token 失效必须触发 HA reauth，而不是普通重试."""
    hass.data.setdefault(DOMAIN, {})
    mock_config_entry.domain = DOMAIN

    mock_client = AsyncMock(spec=YeelightProClient)
    mock_client.check_health.side_effect = auth_error

    with (
        patch("custom_components.yeelight_pro.async_get_clientsession"),
        patch(
            "custom_components.yeelight_pro.YeelightProClient",
            return_value=mock_client,
        ),
    ):
        from custom_components.yeelight_pro import async_setup_entry

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("check_health_error", "expected_error"),
    [
        pytest.param(
            AuthenticationError(
                "token=secret-token https://api.yeelight.com house=12345 device=67890"
            ),
            ConfigEntryAuthFailed,
            id="auth",
        ),
        pytest.param(
            YeelightConnectionError(
                "token=secret-token https://api.yeelight.com house=12345 device=67890"
            ),
            ConfigEntryNotReady,
            id="connection",
        ),
    ],
)
async def test_setup_entry_health_check_error_traceback_redacts_sensitive_cause(
    hass: HomeAssistant,
    mock_config_entry,
    check_health_error: AuthenticationError | YeelightConnectionError,
    expected_error: type[Exception],
) -> None:
    """setup 阶段包装 HA 异常时，不应保留下游敏感 cause."""
    hass.data.setdefault(DOMAIN, {})
    mock_config_entry.domain = DOMAIN

    mock_client = AsyncMock(spec=YeelightProClient)
    mock_client.check_health.side_effect = check_health_error

    with (
        patch("custom_components.yeelight_pro.async_get_clientsession"),
        patch(
            "custom_components.yeelight_pro.YeelightProClient",
            return_value=mock_client,
        ),
    ):
        from custom_components.yeelight_pro import async_setup_entry

        with pytest.raises(expected_error) as exc_info:
            await async_setup_entry(hass, mock_config_entry)

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
@pytest.mark.parametrize(
    "auth_error",
    [
        pytest.param(TokenExpiredError("expired"), id="401-token-expired"),
        pytest.param(AuthenticationError("forbidden"), id="403-forbidden"),
    ],
)
async def test_coordinator_refresh_auth_failure_raises_config_entry_auth_failed(
    hass: HomeAssistant,
    auth_error: AuthenticationError,
) -> None:
    """刷新阶段 token 失效必须保留鉴权语义，触发 HA reauth."""
    mock_client = AsyncMock(spec=YeelightProClient)
    mock_client.get_devices.side_effect = auth_error

    coordinator = YeelightProCoordinator(
        hass=hass,
        client=mock_client,
        house_id=12345,
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_control_methods_pass_configured_house_id(
    hass: HomeAssistant,
) -> None:
    """coordinator 写接口必须把配置条目的 house_id 传给 client."""
    mock_client = AsyncMock(spec=YeelightProClient)
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=mock_client,
        house_id=12345,
    )
    coordinator.devices = {67890: {"id": 67890, "name": "客厅灯"}}
    coordinator.async_request_refresh = AsyncMock()

    await coordinator.async_control_device(
        device_id=67890,
        params={"p": True},
        duration=250,
    )
    mock_client.control_device.assert_awaited_once_with(
        12345,
        67890,
        {"p": True},
        250,
    )

    await coordinator.async_toggle_device(device_id=67890, properties=["p"])
    mock_client.toggle_device.assert_awaited_once_with(12345, 67890, ["p"])
    coordinator.async_request_refresh.assert_awaited_once()

    await coordinator.async_execute_scene("scene_1")
    mock_client.execute_scene.assert_awaited_once_with(12345, "scene_1")

    await coordinator.async_control_group(
        group_id="group_1",
        params={"p": False},
        duration=400,
    )
    mock_client.control_group.assert_awaited_once_with(
        12345,
        "group_1",
        {"p": False},
        400,
    )


@pytest.mark.parametrize("platform", PLATFORMS)
def test_declared_platforms_import_and_expose_setup(platform: str) -> None:
    """PLATFORMS 声明的平台必须都能被 HA 正常加载."""
    module = importlib.import_module(f"custom_components.yeelight_pro.{platform}")
    assert hasattr(module, "async_setup_entry")
