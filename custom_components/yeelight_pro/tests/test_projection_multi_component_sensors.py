"""Multi-component sensor projection tests."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.sensor import project_sensors

from .projection_helpers import DOMAIN, projection_payload


def test_multi_component_sensor_properties_keep_component_scope() -> None:
    """同设备多组件同属性不能互相覆盖，否则 HA 设备页会少实体."""
    device = projection_payload(
        device_id="dual-lux",
        category="other",
        component_id="sensor_1",
        state={"luminance": 120},
        component_category="ambient light sensor",
        properties=("luminance",),
    )
    device["ha_device_instance"]["components"].append({
        "component_id": "sensor_2",
        "name": "右侧",
        "desc": "右侧",
        "category": "ambient light sensor",
        "available": True,
        "state": {"luminance": 240},
    })
    device["ha_product_model"]["components"].append({
        "component_id": "sensor_2",
        "name": "右侧",
        "desc": "右侧",
        "category": "ambient light sensor",
        "properties": [{"prop_id": "luminance", "access": "read"}],
        "events": [],
    })
    device["ha_device_instance"]["components"][0]["name"] = "左侧"
    device["ha_device_instance"]["components"][0]["desc"] = "左侧"
    device["ha_product_model"]["components"][0]["name"] = "左侧"
    device["ha_product_model"]["components"][0]["desc"] = "左侧"

    sensors = project_sensors(device, domain=DOMAIN)

    assert [
        (item.component_id, item.unique_id, item.name, item.native_value)
        for item in sensors
    ] == [
        ("sensor_1_illuminance", "yeelight_pro_dual-lux_sensor_1_illuminance", "左侧 光照", 120),
        ("sensor_2_illuminance", "yeelight_pro_dual-lux_sensor_2_illuminance", "右侧 光照", 240),
    ]


def test_multi_component_binary_sensor_properties_keep_component_scope() -> None:
    """同设备多个人感组件都应生成 binary_sensor，而不是只保留一个 motion."""
    device = projection_payload(
        device_id="dual-motion",
        category="human_sensor",
        component_id="human_1",
        state={"mv": True},
        component_category="human detection sensor",
        properties=("mv",),
    )
    device["ha_device_instance"]["components"].append({
        "component_id": "human_2",
        "name": "右侧",
        "desc": "右侧",
        "category": "human detection sensor",
        "available": True,
        "state": {"mv": False},
    })
    device["ha_product_model"]["components"].append({
        "component_id": "human_2",
        "name": "右侧",
        "desc": "右侧",
        "category": "human detection sensor",
        "properties": [{"prop_id": "mv", "access": "read"}],
        "events": [],
    })
    device["ha_device_instance"]["components"][0]["name"] = "左侧"
    device["ha_device_instance"]["components"][0]["desc"] = "左侧"
    device["ha_product_model"]["components"][0]["name"] = "左侧"
    device["ha_product_model"]["components"][0]["desc"] = "左侧"

    sensors = project_binary_sensors(device, domain=DOMAIN)

    assert [
        (item.component_id, item.unique_id, item.name, item.is_on)
        for item in sensors
    ] == [
        ("human_1_motion", "yeelight_pro_dual-motion_human_1_motion", "左侧 人体移动", True),
        ("human_2_motion", "yeelight_pro_dual-motion_human_2_motion", "右侧 人体移动", False),
    ]
