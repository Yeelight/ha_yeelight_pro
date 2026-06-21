"""Shared helpers for LAN control routing tests."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator


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
