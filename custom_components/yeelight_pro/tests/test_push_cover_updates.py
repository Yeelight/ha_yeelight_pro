"""Push payload integration tests for cover entities."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.cover import YeelightProCover


@pytest.mark.asyncio
async def test_coordinator_applies_wrapped_push_property_updates_to_cover(
    hass: HomeAssistant,
) -> None:
    """包装后的 prop 推送仍应进入 coordinator 并刷新 HA cover 监听器."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228219: {
            "id": 228219,
            "device_id": 228219,
            "name": "S21 Curtain",
            "category": "curtain",
            "type": "curtain",
            "online": None,
            "params": {"cp": 10, "tp": 10},
            "ha_device_instance": {
                "device_id": "228219",
                "name": "S21 Curtain",
                "online": None,
                "components": [
                    {
                        "component_id": "curtain",
                        "category": "curtain",
                        "available": False,
                        "state": {"cp": 10, "tp": 10},
                    }
                ],
            },
            "ha_product_model": {
                "schema_version": "v1",
                "product": {
                    "model_id": "model-curtain",
                    "category": "curtain",
                    "name": "S21 Curtain",
                    "manufacturer": "Yeelight",
                },
                "components": [
                    {
                        "component_id": "curtain",
                        "category": "curtain",
                        "name": "curtain",
                        "properties": [
                            {"prop_id": "cp", "access": "read"},
                            {"prop_id": "tp", "access": "read_write"},
                        ],
                    }
                ],
            },
        }
    }
    coordinator.data = coordinator.devices
    cover = YeelightProCover(coordinator, 228219, component_id="curtain")
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(_listener)

    events = await coordinator.async_handle_push_payload(
        {
            "method": "message",
            "data": {
                "type": "prop",
                "nodes": [
                    {
                        "id": 228219,
                        "nt": 2,
                        "o": True,
                        "properties": [
                            {"propId": "cp", "value": 45},
                            {"propId": "tp", "value": 70},
                        ],
                    }
                ],
            },
        }
    )

    try:
        assert events == []
        assert updates == 1
        refreshed = coordinator.get_device(228219)
        assert refreshed is not None
        assert refreshed["online"] is True
        assert refreshed["params"]["cp"] == 45
        assert refreshed["params"]["tp"] == 70
        assert cover.available is True
        assert cover.current_cover_position == 45
        assert cover.is_opening is True
    finally:
        remove_listener()


@pytest.mark.asyncio
async def test_coordinator_applies_push_property_updates_with_res_id_alias(
    hass: HomeAssistant,
) -> None:
    """私有部署推送使用 resId/deviceId 别名时也应立即刷新 cover 状态."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228220: {
            "id": 228220,
            "device_id": 228220,
            "name": "S21 Curtain",
            "category": "curtain",
            "type": "curtain",
            "online": None,
            "params": {"cp": 10, "tp": 10},
            "ha_device_instance": {
                "device_id": "228220",
                "name": "S21 Curtain",
                "online": None,
                "components": [
                    {
                        "component_id": "curtain",
                        "category": "curtain",
                        "available": False,
                        "state": {"cp": 10, "tp": 10},
                    }
                ],
            },
            "ha_product_model": {
                "schema_version": "v1",
                "product": {
                    "model_id": "model-curtain",
                    "category": "curtain",
                    "name": "S21 Curtain",
                    "manufacturer": "Yeelight",
                },
                "components": [
                    {
                        "component_id": "curtain",
                        "category": "curtain",
                        "name": "curtain",
                        "properties": [
                            {"prop_id": "cp", "access": "read"},
                            {"prop_id": "tp", "access": "read_write"},
                        ],
                    }
                ],
            },
        }
    }
    coordinator.data = coordinator.devices
    cover = YeelightProCover(coordinator, 228220, component_id="curtain")
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(_listener)

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "resId": "228220",
                    "o": True,
                    "properties": [
                        {"propId": "cp", "value": 35},
                        {"propId": "tp", "value": 35},
                    ],
                }
            ],
        }
    )

    try:
        assert events == []
        assert updates == 1
        refreshed = coordinator.get_device(228220)
        assert refreshed is not None
        assert refreshed["online"] is True
        assert refreshed["params"]["cp"] == 35
        assert refreshed["params"]["tp"] == 35
        assert cover.available is True
        assert cover.current_cover_position == 35
    finally:
        remove_listener()


@pytest.mark.asyncio
async def test_coordinator_applies_push_online_only_update_to_cover(
    hass: HomeAssistant,
) -> None:
    """只包含在线状态的私有部署推送也应刷新窗帘 available。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228221: {
            "id": 228221,
            "device_id": 228221,
            "name": "S21 Curtain",
            "category": "curtain",
            "type": "curtain",
            "online": None,
            "params": {"cp": 10, "tp": 10},
            "ha_device_instance": {
                "device_id": "228221",
                "name": "S21 Curtain",
                "online": None,
                "components": [
                    {
                        "component_id": "curtain",
                        "category": "curtain",
                        "available": False,
                        "state": {"cp": 10, "tp": 10},
                    }
                ],
            },
        }
    }
    coordinator.data = coordinator.devices
    cover = YeelightProCover(coordinator, 228221, component_id="curtain")
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(_listener)

    events = await coordinator.async_handle_push_payload(
        {
            "method": "message",
            "data": {
                "type": "prop",
                "nodeId": "228221",
                "o": True,
                "propName": "o",
                "value": True,
            },
        }
    )

    try:
        assert events == []
        assert updates == 1
        refreshed = coordinator.get_device(228221)
        assert refreshed is not None
        assert refreshed["online"] is True
        assert refreshed["ha_device_instance"]["online"] is True
        assert refreshed["ha_device_instance"]["components"][0]["available"] is True
        assert cover.available is True
        assert cover.current_cover_position == 10
    finally:
        remove_listener()
