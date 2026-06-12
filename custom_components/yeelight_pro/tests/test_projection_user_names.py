"""Projection boundaries for user-defined names."""
from __future__ import annotations

from custom_components.yeelight_pro.projector.sensor import project_sensors

from .projection_helpers import DOMAIN, projection_payload


def test_user_name_does_not_block_unknown_sensor_fallback() -> None:
    """未知 fallback 只看物模型身份，不能被用户名称中的情景/旋钮误伤。"""
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

    assert [item.component_id for item in projections] == ["unknown_vendor_private"]
