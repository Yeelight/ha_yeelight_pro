"""LAN-only device action routing tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.exceptions import CommandError


@pytest.mark.asyncio
async def test_coordinator_action_device_uses_connected_lan_runtime(
    hass: HomeAssistant,
) -> None:
    """设备 action 是 LAN-only 路径，应发送 gateway_set.prop action 节点。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    coordinator.async_request_refresh = AsyncMock()
    lan_runtime = _connected_lan_runtime()
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_action_device(
        device_id=67890,
        action={"motorAdjust": {"type": "pause"}},
    )

    lan_runtime.async_set_properties.assert_awaited_once_with(
        [{"id": 67890, "nt": 2, "action": {"motorAdjust": {"type": "pause"}}}]
    )
    mock_client.control_device.assert_not_awaited()
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_action_device_does_not_fallback_to_cloud(
    hass: HomeAssistant,
) -> None:
    """LAN 不可用时 action 不走未确认的云端 fallback。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    coordinator.async_request_refresh = AsyncMock()
    lan_runtime = _connected_lan_runtime(connected=False)
    coordinator.set_lan_runtime(lan_runtime)

    with pytest.raises(CommandError) as exc_info:
        await coordinator.async_action_device(
            device_id=67890,
            action={"motorAdjust": {"type": "pause"}},
        )

    assert str(exc_info.value) == (
        "LAN action is unavailable for this Yeelight Pro entry"
    )
    lan_runtime.async_set_properties.assert_not_awaited()
    mock_client.control_device.assert_not_awaited()
    coordinator.async_request_refresh.assert_not_awaited()


def test_coordinator_reports_action_capability_from_lan_health(
    hass: HomeAssistant,
) -> None:
    """STOP feature 使用 coordinator 对当前 LAN action 能力的判断。"""
    coordinator, _mock_client = _coordinator_with_device(hass)

    coordinator.set_lan_runtime(_connected_lan_runtime())
    assert coordinator.can_control_device_action() is True

    coordinator.set_lan_runtime(_connected_lan_runtime(connected=False))
    assert coordinator.can_control_device_action() is False


@pytest.mark.asyncio
async def test_coordinator_lan_action_error_is_redacted(
    hass: HomeAssistant,
) -> None:
    """LAN action 失败只暴露异常类型，不泄漏 host/token/device 文本。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    coordinator.async_request_refresh = AsyncMock()
    lan_runtime = _connected_lan_runtime()
    lan_runtime.async_set_properties.side_effect = RuntimeError(
        "192.168.1.20 token=secret device=67890"
    )
    coordinator.set_lan_runtime(lan_runtime)

    with pytest.raises(CommandError) as exc_info:
        await coordinator.async_action_device(
            device_id=67890,
            action={"motorAdjust": {"type": "pause"}},
        )

    message = str(exc_info.value)
    assert message == "Failed to device action over LAN: RuntimeError"
    assert "192.168.1.20" not in message
    assert "secret" not in message
    assert "67890" not in message
    mock_client.control_device.assert_not_awaited()
    coordinator.async_request_refresh.assert_not_awaited()


def _coordinator_with_device(
    hass: HomeAssistant,
) -> tuple[YeelightProCoordinator, AsyncMock]:
    """Return a coordinator with one known device and a spec-bound client mock."""
    mock_client = AsyncMock(spec=YeelightProClient)
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=mock_client,
        house_id=12345,
    )
    coordinator.devices = {67890: {"id": 67890, "name": "客厅灯"}}
    return coordinator, mock_client


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
