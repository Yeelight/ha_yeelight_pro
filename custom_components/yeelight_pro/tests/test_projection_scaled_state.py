"""Runtime scaled state projection regression tests."""

from __future__ import annotations

from custom_components.yeelight_pro.converter.device import (
    YeelightLanDeviceInstanceConverter,
)
from custom_components.yeelight_pro.converter.product import (
    YeelightProductSchemaConverter,
)
from custom_components.yeelight_pro.projector.sensor import project_sensors

from .projection_helpers import DOMAIN


def test_sensor_projection_uses_schema_scaled_runtime_state() -> None:
    """sensor 投影应使用物模型缩放后的 canonical state，而非 raw params。"""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1012,
            "name": "Scaled telemetry",
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
    )
    device_instance = YeelightLanDeviceInstanceConverter().convert(
        {
            "id": "scaled-power-1",
            "name": "Scaled Power",
            "pid": 1012,
            "category": "other",
            "type": "sensor",
            "online": True,
            "params": {
                "curp": "12",
                "iec": 2500,
            },
        },
        product_model=product,
    )
    device = {
        "id": "scaled-power-1",
        "device_id": "scaled-power-1",
        "name": "Scaled Power",
        "category": "other",
        "type": "sensor",
        "online": True,
        "params": {
            "curp": "12",
            "iec": 2500,
        },
        "ha_device_instance": device_instance.to_dict(),
        "ha_product_model": product.to_dict(),
    }

    projections = project_sensors(device, domain=DOMAIN)
    by_component = {projection.component_id: projection for projection in projections}

    assert by_component["current_power"].native_value == 120
    assert by_component["energy_consumption"].native_value == 25.0
