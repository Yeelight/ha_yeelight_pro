"""Projection boundaries for user-defined names."""
from __future__ import annotations

from custom_components.yeelight_pro.projector.sensor import project_sensors

from .projection_helpers import DOMAIN, projection_payload


def test_user_name_does_not_enable_unknown_sensor_projection() -> None:
    """未知能力不能因为用户名称避开过滤或生成泛化 sensor。"""
    device = projection_payload(
        device_id="named-panel-sensor-1",
        category="light_sensor",
        component_id="vendor_meter",
        state={"vendor_private": 7},
        params={"vendor_private": 7},
        component_category="vendor meter",
    )
    device["name"] = "玄关情景面板"
    device["ha_device_instance"]["name"] = "玄关情景面板"
    device["hide_unknown_entities"] = False

    projections = project_sensors(device, domain=DOMAIN)

    assert projections == []
