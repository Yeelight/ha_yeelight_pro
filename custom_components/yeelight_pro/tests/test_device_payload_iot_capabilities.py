"""Runtime device payload capability classification tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder


def test_runtime_payload_light_sensor_bundle_ignores_user_device_name() -> None:
    """设备名不能覆盖易来物模型能力组合，光照传感器属性应显示为照度设备。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 406,
                "name": "厨房烟雾传感器",
                "category": "light",
                "pid": 4060,
                "roomId": 1,
                "properties": [
                    {"propId": "mv", "value": True},
                    {"propId": "luminance", "value": 188},
                    {"propId": "sens_range", "value": 3},
                    {"propId": "lumi_setting", "value": 120},
                    {"propId": "delay_time", "value": 30},
                ],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "1", "name": "厨房"}],
    )

    device = data[406]

    assert device["iot_category"] == "light_sensor"
    assert device["ha_platform"] == "sensor"
    assert device["ha_platform_candidates"] == ["sensor", "binary_sensor"]
    assert device["device_info"]["model"] == "照度传感器"
    assert device["device_info"]["suggested_area"] == "厨房"
