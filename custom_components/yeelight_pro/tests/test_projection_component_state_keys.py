"""Component-scoped runtime state key projection regressions."""

from __future__ import annotations

import logging

from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.fan import project_fans
from custom_components.yeelight_pro.projector.light import project_lights
from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, projection_payload


def test_multi_component_sensor_reads_component_scoped_state_keys() -> None:
    """组件 state 稀疏时 sensor 应读取 N-prop 原始键."""
    device = projection_payload(
        device_id="dual-lux-scoped",
        category="other",
        component_id="sensor_1",
        state={},
        params={"1-luminance": 120, "2-luminance": 240},
        component_category="ambient light sensor",
        properties=("luminance",),
    )
    _add_second_component(
        device,
        component_id="sensor_2",
        category="ambient light sensor",
        prop_id="luminance",
    )
    device["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "sensor_1": {"luminance": "1-luminance"},
            "sensor_2": {"luminance": "2-luminance"},
        }
    }

    sensors = project_sensors(device, domain=DOMAIN)

    assert [(item.component_id, item.native_value) for item in sensors] == [
        ("sensor_1_illuminance", 120),
        ("sensor_2_illuminance", 240),
    ]


def test_multi_component_binary_sensor_reads_component_scoped_state_keys() -> None:
    """组件 state 稀疏时 binary_sensor 应读取 N-prop 原始键."""
    device = projection_payload(
        device_id="dual-motion-scoped",
        category="human_sensor",
        component_id="human_1",
        state={},
        params={"1-mv": True, "2-mv": False},
        component_category="human detection sensor",
        properties=("mv",),
    )
    _add_second_component(
        device,
        component_id="human_2",
        category="human detection sensor",
        prop_id="mv",
    )
    device["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "human_1": {"mv": "1-mv"},
            "human_2": {"mv": "2-mv"},
        }
    }

    sensors = project_binary_sensors(device, domain=DOMAIN)

    assert [(item.component_id, item.is_on) for item in sensors] == [
        ("human_1_motion", True),
        ("human_2_motion", False),
    ]


def test_component_scoped_state_read_logs_redacted_context(caplog) -> None:
    """组件 scoped key 调试日志不能输出用户名称或属性值."""
    device = projection_payload(
        device_id="dual-lux-scoped-log",
        category="other",
        component_id="sensor_1",
        state={},
        params={"1-luminance": 120, "2-luminance": 240},
        component_category="ambient light sensor",
        properties=("luminance",),
    )
    device["name"] = "用户自定义照度名称"
    _add_second_component(
        device,
        component_id="sensor_2",
        category="ambient light sensor",
        prop_id="luminance",
    )
    device["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "sensor_1": {"luminance": "1-luminance"},
            "sensor_2": {"luminance": "2-luminance"},
        }
    }

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.projector.common",
    ):
        project_sensors(device, domain=DOMAIN)

    assert "action=component_scoped_state_read" in caplog.text
    assert "device_id=dual-lux-scoped-log" in caplog.text
    assert "component_id=sensor_2" in caplog.text
    assert "control_key=2-luminance" in caplog.text
    assert "用户自定义照度名称" not in caplog.text
    assert "240" not in caplog.text


def test_light_reads_component_scoped_state_keys() -> None:
    """灯光组件 state 稀疏时应读取 N-p/N-l/N-ct 原始键."""
    device = _component_scoped_payload(
        device_id="light-scoped",
        category="light",
        component_id="light_1",
        component_category="color temperature light",
        params={"1-p": True, "1-l": 80, "1-ct": 4000},
        prop_ids=("p", "l", "ct"),
        key_map={"p": "1-p", "l": "1-l", "ct": "1-ct"},
    )

    [light] = project_lights(device, domain=DOMAIN)

    assert light.is_on is True
    assert light.brightness == 203
    assert light.color_temp == 250
    assert light.power_key == "1-p"
    assert light.brightness_key == "1-l"
    assert light.color_temp_key == "1-ct"


def test_switch_reads_component_scoped_state_key() -> None:
    """继电器组件 state 稀疏时 switch 应读取 N-p 原始键."""
    device = _component_scoped_payload(
        device_id="switch-scoped",
        category="relay_switch",
        component_id="relay_switch_1",
        component_category="switch control",
        params={"1-p": True},
        prop_ids=("p",),
        key_map={"p": "1-p"},
    )

    [switch] = project_switches(device, domain=DOMAIN)

    assert switch.is_on is True
    assert switch.control_key == "1-p"


def test_fan_reads_component_scoped_state_keys() -> None:
    """新风组件 state 稀疏时 fan 应读取 N-vmcp/N-vmcf 原始键."""
    device = _component_scoped_payload(
        device_id="fan-scoped",
        category="temp_control",
        component_id="fresh_air",
        component_category="fresh air",
        params={"1-vmcp": True, "1-vmcf": 30},
        prop_ids=("vmcp", "vmcf"),
        key_map={"vmcp": "1-vmcp", "vmcf": "1-vmcf"},
    )

    [fan] = project_fans(device, domain=DOMAIN)

    assert fan.is_on is True
    assert fan.percentage == 30
    assert fan.power_key == "1-vmcp"
    assert fan.speed_key == "1-vmcf"


def test_property_controls_read_component_scoped_state_keys() -> None:
    """配置类 number/select/switch 也应读取 N-prop 当前值."""
    device = _component_scoped_payload(
        device_id="controls-scoped",
        category="curtain",
        component_id="curtain_1",
        component_category="zebra blinds",
        params={"1-rg": 4, "1-rd": "1", "1-li": 1},
        prop_ids=("rg", "rd", "li"),
        key_map={"rg": "1-rg", "rd": "1-rd", "li": "1-li"},
    )
    props = device["ha_product_model"]["components"][0]["properties"]
    props[0].update({
        "name": "旋转档位",
        "property_type": "int",
        "value_range": {"min": 1, "max": 10, "step": 1},
    })
    props[1].update({
        "name": "电机方向",
        "property_type": "enum",
        "value_list": [
            {"code": "0", "desc": "正向"},
            {"code": "1", "desc": "反向"},
        ],
    })
    props[2].update({"name": "指示灯", "property_type": "int"})

    [number] = project_number_controls(device, domain=DOMAIN)
    [select] = project_select_controls(device, domain=DOMAIN)
    [switch] = project_switch_controls(device, domain=DOMAIN)

    assert number.value == 4
    assert number.control_key == "1-rg"
    assert select.value == "1"
    assert select.control_key == "1-rd"
    assert switch.is_on is True
    assert switch.control_key == "1-li"


def _add_second_component(
    device: dict,
    *,
    component_id: str,
    category: str,
    prop_id: str,
) -> None:
    """Add a second sparse component with product-schema property evidence."""
    device["ha_device_instance"]["components"].append({
        "component_id": component_id,
        "name": "右侧",
        "desc": "右侧",
        "category": category,
        "available": True,
        "state": {},
    })
    device["ha_product_model"]["components"].append({
        "component_id": component_id,
        "name": "右侧",
        "desc": "右侧",
        "category": category,
        "properties": [{"prop_id": prop_id, "access": "read"}],
        "events": [],
    })
    device["ha_device_instance"]["components"][0]["name"] = "左侧"
    device["ha_device_instance"]["components"][0]["desc"] = "左侧"
    device["ha_product_model"]["components"][0]["name"] = "左侧"
    device["ha_product_model"]["components"][0]["desc"] = "左侧"


def _component_scoped_payload(
    *,
    device_id: str,
    category: str,
    component_id: str,
    component_category: str,
    params: dict[str, object],
    prop_ids: tuple[str, ...],
    key_map: dict[str, str],
) -> dict:
    """Build a schema-backed single component whose runtime state is sparse."""
    device = projection_payload(
        device_id=device_id,
        category=category,
        component_id=component_id,
        state={},
        params=params,
        component_category=component_category,
        properties=prop_ids,
    )
    device["ha_device_instance"]["extensions"] = {
        "component_state_keys": {component_id: key_map}
    }
    device["ha_product_model"]["components"][0]["name"] = component_category
    device["ha_product_model"]["components"][0]["component_type"] = component_category
    for prop in device["ha_product_model"]["components"][0]["properties"]:
        prop["access"] = "read_write"
        if prop["prop_id"] in {"l", "vmcf"}:
            prop["value_range"] = {"min": 1, "max": 100, "step": 1}
        if prop["prop_id"] == "ct":
            prop["value_range"] = {"min": 2700, "max": 6500, "step": 1}
    return device
