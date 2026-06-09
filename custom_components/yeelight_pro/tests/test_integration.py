"""Lightweight integration smoke tests."""
from __future__ import annotations

from importlib import import_module
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN, PLATFORMS
from custom_components.yeelight_pro.core.client import YeelightProClient


@pytest.fixture
def mock_client() -> AsyncMock:
    """Build a client test double."""
    client = AsyncMock(spec=YeelightProClient)
    client.control_device.return_value = True
    client.execute_scene.return_value = True
    client.get_devices.return_value = []
    return client


@pytest.mark.asyncio
async def test_platform_setup(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """All declared platforms should expose async_setup_entry."""
    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "client": mock_coordinator.client,
            "coordinator": mock_coordinator,
        }
    }

    for platform in PLATFORMS:
        module = import_module(f"custom_components.yeelight_pro.{platform}")
        assert hasattr(module, "async_setup_entry")


@pytest.mark.asyncio
async def test_client_api(mock_client: AsyncMock) -> None:
    """Client command API test double should match expected async surface."""
    assert await mock_client.control_device(
        house_id=12345,
        device_id=12345,
        params={"power": "on"},
    ) is True

    assert await mock_client.execute_scene(house_id=12345, scene_id="scene_1") is True

    devices = await mock_client.get_devices(house_id=12345)
    assert isinstance(devices, list)


@pytest.mark.asyncio
async def test_coordinator_services(mock_coordinator: MagicMock) -> None:
    """Coordinator service methods should remain async-callable."""
    await mock_coordinator.async_execute_scene(scene_id="scene_1")
    mock_coordinator.async_execute_scene.assert_called_once_with(scene_id="scene_1")

    await mock_coordinator.async_trigger_automation(automation_id="auto_1")
    mock_coordinator.async_trigger_automation.assert_called_once_with(
        automation_id="auto_1"
    )

    await mock_coordinator.async_control_device(
        device_id=12345,
        params={"power": "on"},
    )
    mock_coordinator.async_control_device.assert_called_once_with(
        device_id=12345,
        params={"power": "on"},
    )
