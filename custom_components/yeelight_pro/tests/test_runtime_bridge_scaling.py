"""Runtime bridge scaling and event dedupe tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.runtime_bridge import (
    RuntimeEventDeduper,
    runtime_event_dedupe_key,
)
from custom_components.yeelight_pro.projector.sensor import project_sensors

@pytest.mark.asyncio
async def test_lan_runtime_update_rebuilds_scaled_canonical_state(
    hass: HomeAssistant,
) -> None:
    """LAN 更新后 canonical state 仍应按 product schema 保持实际值。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228218: {
            "id": 228218,
            "device_id": 228218,
            "name": "LAN Power Meter",
            "category": "other",
            "type": "sensor",
            "online": True,
            "pid": 1012,
            "product_schema": _power_meter_schema(),
            "params": {"curp": 10, "iec": 1000},
        }
    }
    DevicePayloadBuilder().attach_canonical_models_if_available(
        coordinator.devices[228218]
    )
    coordinator.data = coordinator.devices

    await coordinator.async_handle_lan_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [
                {
                    "id": 228218,
                    "nt": 2,
                    "params": {"curp": "12", "iec": 2500},
                }
            ],
        }
    )

    refreshed = coordinator.get_device(228218)
    assert refreshed is not None
    assert refreshed["params"] == {"curp": "12", "iec": 2500}
    assert refreshed["ha_device_instance"]["components"][0]["state"] == {
        "curp": 120,
        "iec": 25.0,
    }
    by_component = {
        projection.component_id: projection
        for projection in project_sensors(refreshed, domain=DOMAIN)
    }
    assert by_component["current_power"].native_value == 120
    assert by_component["energy_consumption"].native_value == 25.0


@pytest.mark.asyncio
async def test_lan_runtime_update_scales_temperature_humidity_raw_value(
    hass: HomeAssistant,
) -> None:
    """LAN type=136 后续属性推送也必须按协议把 t/100。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228219: {
            "id": 228219,
            "device_id": 228219,
            "name": "LAN Temp Humidity",
            "category": "other",
            "type": "other",
            "online": True,
            "lan_type": 136,
            "params": {"t": 0.0, "h": 0},
            "ha_device_instance": {
                "device_id": "228219",
                "name": "LAN Temp Humidity",
                "online": True,
                "components": [
                    {
                        "component_id": "temp_humidity",
                        "category": "temperature humidity sensor",
                        "available": True,
                        "state": {"t": 0.0, "h": 0},
                    }
                ],
            },
        }
    }
    coordinator.data = coordinator.devices

    await coordinator.async_handle_lan_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [{"id": 228219, "nt": 2, "params": {"t": 2534, "h": 58}}],
        }
    )

    refreshed = coordinator.get_device(228219)
    assert refreshed is not None
    assert refreshed["params"] == {"t": 25.34, "h": 58}
    assert refreshed["ha_device_instance"]["components"][0]["state"] == {
        "t": 25.34,
        "h": 58,
    }
    by_component = {
        projection.component_id: projection
        for projection in project_sensors(refreshed, domain=DOMAIN)
    }
    assert by_component["temperature"].native_value == 25.34


def test_runtime_event_dedupe_key_is_bounded_and_identifier_safe() -> None:
    """事件去重键不能包含 msgId、设备 ID 或原始事件值。"""
    payload = {
        "source_device_id": "device-secret",
        "component_id": "scene_panel",
        "event_type": "click",
        "event_attributes": {
            "message_id": "message-secret",
            "raw_event": "raw-secret",
        },
    }

    key = runtime_event_dedupe_key(payload)
    deduper = RuntimeEventDeduper(max_keys=1)

    assert isinstance(key, str)
    assert key
    assert "message-secret" not in key
    assert "device-secret" not in key
    assert "raw-secret" not in key
    assert deduper.is_duplicate(payload) is False
    assert deduper.is_duplicate(payload) is True


def _power_meter_schema() -> dict:
    """构造运行时 bridge 测试用缩放遥测 schema。"""
    return {
        "pid": 1012,
        "name": "LAN Power Meter Product",
        "category": "other",
        "components": [
            {
                "cid": 63,
                "name": "power meter",
                "type": 0,
                "category": "power meter",
                "properties": [
                    {
                        "propId": "curp",
                        "format": "int",
                        "access": 5,
                        "zoom": -1,
                        "scale": 10,
                    },
                    {
                        "propId": "iec",
                        "format": "int",
                        "access": 5,
                        "zoom": 1,
                        "scale": 100,
                    },
                ],
            }
        ],
    }
