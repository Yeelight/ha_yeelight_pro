"""P0 Home Assistant runtime auth/control regression tests."""
from __future__ import annotations

import asyncio
from contextlib import suppress
import importlib
import traceback
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from custom_components.yeelight_pro.const import DOMAIN, PLATFORMS
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    CommandError,
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


@pytest.mark.asyncio
async def test_coordinator_control_device_updates_state_before_cloud_ack(
    hass: HomeAssistant,
) -> None:
    """云端 ACK 慢时，HA 侧状态应先乐观刷新，避免等待轮询周期。"""
    command_started = asyncio.Event()
    allow_command_finish = asyncio.Event()

    async def _slow_control_device(*_args: Any, **_kwargs: Any) -> bool:
        command_started.set()
        await allow_command_finish.wait()
        return True

    mock_client = AsyncMock(spec=YeelightProClient)
    mock_client.control_device.side_effect = _slow_control_device
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=mock_client,
        house_id=12345,
    )
    device = _device_with_switch_state(False)
    coordinator.devices = {67890: device}
    coordinator.async_update_listeners = MagicMock()

    task = asyncio.create_task(
        coordinator.async_control_device(
            device_id=67890,
            params={"p": True},
            duration=250,
        )
    )
    try:
        await asyncio.wait_for(command_started.wait(), timeout=1)

        assert device["params"]["p"] is True
        assert device["ha_device_instance"]["components"][0]["state"]["p"] is True
        coordinator.async_update_listeners.assert_called_once()
    finally:
        allow_command_finish.set()
        with suppress(Exception):
            await task


@pytest.mark.asyncio
async def test_coordinator_control_device_rolls_back_failed_cloud_update(
    hass: HomeAssistant,
) -> None:
    """云端控制失败时，应撤销已乐观合并的本地状态。"""
    mock_client = AsyncMock(spec=YeelightProClient)
    mock_client.control_device.side_effect = CommandError("rejected")
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=mock_client,
        house_id=12345,
    )
    device = _device_with_switch_state(False)
    coordinator.devices = {67890: device}
    coordinator.async_update_listeners = MagicMock()

    with pytest.raises(CommandError):
        await coordinator.async_control_device(
            device_id=67890,
            params={"p": True},
            duration=250,
        )

    assert device["params"]["p"] is False
    assert device["ha_device_instance"]["components"][0]["state"]["p"] is False
    assert 67890 not in coordinator._runtime_state.overrides
    assert coordinator.async_update_listeners.call_count == 2


@pytest.mark.asyncio
async def test_coordinator_control_device_uses_connected_lan_runtime(
    hass: HomeAssistant,
) -> None:
    """本地网关已连接时，设备属性控制应走 LAN gateway_set.prop。"""
    mock_client = AsyncMock(spec=YeelightProClient)
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=mock_client,
        house_id=12345,
    )
    coordinator.devices = {67890: {"id": 67890, "name": "客厅灯"}}
    lan_runtime = _connected_lan_runtime()
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_control_device(
        device_id=67890,
        params={"p": True},
        duration=250,
    )

    lan_runtime.async_set_properties.assert_awaited_once_with([
        {"id": 67890, "nt": 2, "duration": 250, "set": {"p": True}}
    ])
    mock_client.control_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_control_device_falls_back_to_cloud_when_lan_disconnected(
    hass: HomeAssistant,
) -> None:
    """LAN runtime 未连接时保持既有云端控制路径。"""
    mock_client = AsyncMock(spec=YeelightProClient)
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=mock_client,
        house_id=12345,
    )
    coordinator.devices = {67890: {"id": 67890, "name": "客厅灯"}}
    lan_runtime = _connected_lan_runtime(connected=False)
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_control_device(
        device_id=67890,
        params={"p": True},
        duration=250,
    )

    lan_runtime.async_set_properties.assert_not_awaited()
    mock_client.control_device.assert_awaited_once_with(
        12345,
        67890,
        {"p": True},
        250,
    )


@pytest.mark.asyncio
async def test_coordinator_lan_control_error_is_redacted(
    hass: HomeAssistant,
) -> None:
    """LAN 控制失败只暴露异常类型，不泄漏 host/token/device 文本。"""
    mock_client = AsyncMock(spec=YeelightProClient)
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=mock_client,
        house_id=12345,
    )
    coordinator.devices = {67890: {"id": 67890, "name": "客厅灯"}}
    lan_runtime = _connected_lan_runtime()
    lan_runtime.async_set_properties.side_effect = OSError(
        "192.168.1.20 token=secret device=67890"
    )
    coordinator.set_lan_runtime(lan_runtime)

    with pytest.raises(CommandError) as exc_info:
        await coordinator.async_control_device(
            device_id=67890,
            params={"p": True},
            duration=250,
        )

    message = str(exc_info.value)
    assert message == "Failed to control device over LAN: OSError"
    assert "192.168.1.20" not in message
    assert "secret" not in message
    assert "67890" not in message
    mock_client.control_device.assert_not_awaited()


def _connected_lan_runtime(*, connected: bool = True) -> Any:
    """Return a LAN runtime double with diagnostics-style health."""
    return SimpleNamespace(
        async_set_properties=AsyncMock(),
        health=SimpleNamespace(
            as_dict=MagicMock(
                return_value={
                    "running": True,
                    "connected": connected,
                    "sent_count": 0,
                    "received_count": 0,
                    "last_error_type": None,
                }
            )
        ),
    )


def _device_with_switch_state(is_on: bool) -> dict[str, Any]:
    """Return a minimal canonical switch payload for coordinator tests."""
    return {
        "id": 67890,
        "params": {"p": is_on},
        "ha_device_instance": {
            "online": True,
            "components": [
                {
                    "component_id": "switch_control",
                    "available": True,
                    "state": {"p": is_on},
                }
            ],
        },
    }


@pytest.mark.parametrize("platform", PLATFORMS)
def test_declared_platforms_import_and_expose_setup(platform: str) -> None:
    """PLATFORMS 声明的平台必须都能被 HA 正常加载."""
    module = importlib.import_module(f"custom_components.yeelight_pro.{platform}")
    assert hasattr(module, "async_setup_entry")
