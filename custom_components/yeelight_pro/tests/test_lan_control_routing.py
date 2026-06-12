"""LAN-first coordinator control routing tests."""

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
async def test_coordinator_toggle_device_uses_connected_lan_runtime(
    hass: HomeAssistant,
) -> None:
    """LAN 已连接时，设备 toggle 应走 gateway_set.prop。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    coordinator.async_request_refresh = AsyncMock()
    lan_runtime = _connected_lan_runtime()
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_toggle_device(device_id=67890, properties=["p"])

    lan_runtime.async_set_properties.assert_awaited_once_with(
        [{"id": 67890, "nt": 2, "toggle": ["p"]}]
    )
    mock_client.toggle_device.assert_not_awaited()
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_toggle_device_falls_back_to_cloud_when_lan_disconnected(
    hass: HomeAssistant,
) -> None:
    """LAN 未连接时，toggle 保持云端 fallback。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    coordinator.async_request_refresh = AsyncMock()
    lan_runtime = _connected_lan_runtime(connected=False)
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_toggle_device(device_id=67890, properties=["p"])

    lan_runtime.async_set_properties.assert_not_awaited()
    mock_client.toggle_device.assert_awaited_once_with(12345, 67890, ["p"])
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_toggle_device_falls_back_when_lan_health_is_unreadable(
    hass: HomeAssistant,
) -> None:
    """LAN health 不可读时应视为不可用并回退云端，不泄漏诊断异常。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    coordinator.async_request_refresh = AsyncMock()
    lan_runtime = _connected_lan_runtime()
    lan_runtime.health.as_dict.side_effect = RuntimeError(
        "192.168.1.20 token=secret device=67890"
    )
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_toggle_device(device_id=67890, properties=["p"])

    lan_runtime.async_set_properties.assert_not_awaited()
    mock_client.toggle_device.assert_awaited_once_with(12345, 67890, ["p"])
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_lan_toggle_error_is_redacted(
    hass: HomeAssistant,
) -> None:
    """LAN toggle 失败不能静默云端兜底，且错误只暴露异常类型。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    coordinator.async_request_refresh = AsyncMock()
    lan_runtime = _connected_lan_runtime()
    lan_runtime.async_set_properties.side_effect = OSError(
        "192.168.1.20 token=secret device=67890"
    )
    coordinator.set_lan_runtime(lan_runtime)

    with pytest.raises(CommandError) as exc_info:
        await coordinator.async_toggle_device(device_id=67890, properties=["p"])

    message = str(exc_info.value)
    assert message == "Failed to toggle device over LAN: OSError"
    assert "192.168.1.20" not in message
    assert "secret" not in message
    assert "67890" not in message
    mock_client.toggle_device.assert_not_awaited()
    coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_control_group_uses_connected_lan_for_numeric_group_id(
    hass: HomeAssistant,
) -> None:
    """LAN 已连接且 group id 可转数字时，灯组控制应走 nt=4 并更新本地灯组状态。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    coordinator.groups = [{"id": 146, "name": "客厅灯组", "params": {"p": True}}]
    listener = MagicMock()
    remove_listener = coordinator.async_add_listener(listener)
    lan_runtime = _connected_lan_runtime()
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_control_group(
        group_id="146",
        params={"p": False},
        duration=300,
    )

    lan_runtime.async_set_properties.assert_awaited_once_with(
        [{"id": 146, "nt": 4, "duration": 300, "set": {"p": False}}]
    )
    mock_client.control_group.assert_not_awaited()
    assert coordinator.groups[0]["params"] == {"p": False}
    listener.assert_called_once()
    remove_listener()


@pytest.mark.asyncio
async def test_coordinator_control_group_falls_back_to_cloud_for_cloud_group_id(
    hass: HomeAssistant,
) -> None:
    """非数字云端 group id 不伪装成本地 id，应回到云端路径。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    lan_runtime = _connected_lan_runtime()
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_control_group(
        group_id="group_1",
        params={"p": False},
        duration=300,
    )

    lan_runtime.async_set_properties.assert_not_awaited()
    mock_client.control_group.assert_awaited_once_with(
        12345,
        "group_1",
        {"p": False},
        300,
    )


@pytest.mark.asyncio
async def test_coordinator_execute_scene_uses_connected_lan_for_numeric_scene_id(
    hass: HomeAssistant,
) -> None:
    """LAN 已连接且 scene id 可转数字时，场景执行应走 scenes payload。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    lan_runtime = _connected_lan_runtime()
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_execute_scene("413")

    lan_runtime.async_set_properties.assert_awaited_once_with(
        [],
        scenes=[{"id": 413, "duration": 500}],
    )
    mock_client.execute_scene.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_execute_scene_falls_back_to_cloud_for_cloud_scene_id(
    hass: HomeAssistant,
) -> None:
    """非数字云端 scene id 不伪装成本地 id，应回到云端路径。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    lan_runtime = _connected_lan_runtime()
    coordinator.set_lan_runtime(lan_runtime)

    await coordinator.async_execute_scene("scene_1")

    lan_runtime.async_set_properties.assert_not_awaited()
    mock_client.execute_scene.assert_awaited_once_with(12345, "scene_1")


@pytest.mark.asyncio
async def test_coordinator_lan_scene_error_is_redacted(
    hass: HomeAssistant,
) -> None:
    """LAN scene 失败不能静默云端兜底，且错误只暴露异常类型。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    lan_runtime = _connected_lan_runtime()
    lan_runtime.async_set_properties.side_effect = RuntimeError(
        "192.168.1.20 token=secret scene=413"
    )
    coordinator.set_lan_runtime(lan_runtime)

    with pytest.raises(CommandError) as exc_info:
        await coordinator.async_execute_scene("413")

    message = str(exc_info.value)
    assert message == "Failed to execute scene over LAN: RuntimeError"
    assert "192.168.1.20" not in message
    assert "secret" not in message
    assert "413" not in message
    mock_client.execute_scene.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_lan_group_control_error_is_redacted(
    hass: HomeAssistant,
) -> None:
    """LAN 灯组控制失败只暴露异常类型，不泄漏 host/token/group 文本。"""
    coordinator, mock_client = _coordinator_with_device(hass)
    lan_runtime = _connected_lan_runtime()
    lan_runtime.async_set_properties.side_effect = RuntimeError(
        "192.168.1.20 token=secret group=146"
    )
    coordinator.set_lan_runtime(lan_runtime)

    with pytest.raises(CommandError) as exc_info:
        await coordinator.async_control_group(
            group_id="146",
            params={"p": False},
            duration=300,
        )

    message = str(exc_info.value)
    assert message == "Failed to control group over LAN: RuntimeError"
    assert "192.168.1.20" not in message
    assert "secret" not in message
    assert "146" not in message
    mock_client.control_group.assert_not_awaited()


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
