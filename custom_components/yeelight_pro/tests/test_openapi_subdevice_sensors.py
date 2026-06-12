"""OpenAPI subDeviceList sensor projection regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates

from .openapi_subdevice_helpers import build_openapi_device as _build_device
from .openapi_subdevice_helpers import openapi_prop as _prop


def test_openapi_subdevice_sensor_properties_create_sensor_entities() -> None:
    """传感器子设备属性应映射为 HA sensor/binary_sensor 候选。"""
    device = _build_device(
        {
            "id": 9004,
            "name": "走廊人体传感器",
            "category": "human_sensor",
            "subDeviceList": [
                {
                    "index": 1,
                    "name": "human body infrared sensor",
                    "category": "human_sensor",
                    "properties": [
                        _prop("mv", True, "人体移动", "boolean"),
                        _prop("luminance", 321, "照度", "uint16", unit="lx"),
                        _prop("bl", 88, "电量", "uint8", unit="%"),
                    ],
                }
            ],
        }
    )

    candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    }

    assert candidates == {
        ("binary_sensor", "motion"),
        ("sensor", "illuminance"),
        ("sensor", "battery"),
    }
