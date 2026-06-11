"""OpenAPI component category and property conflict regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.projector.light import project_lights
from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)

from .openapi_subdevice_helpers import build_openapi_device as _build_device
from .openapi_subdevice_helpers import candidate_platform_components as _candidates
from .openapi_subdevice_helpers import openapi_prop as _prop


def _wireless_switch_channel_device() -> dict:
    """Build the documented Yeelight wireless switch channel conflict case."""
    return _build_device(
        {
            "id": 100016,
            "name": "无线开关通道",
            "category": "light",
            "subDeviceList": [
                {
                    "index": 1,
                    "category": "relay_switch",
                    "name": "wireless switch channel",
                    "properties": [
                        _prop("l", 1, "亮度", "int", operators=["set"]),
                        _prop("slisaon", 1, "是否开启闪断", "uint8", operators=["set"]),
                        _prop("slisaon_rdy", True, "是否支持闪断", "boolean"),
                        _prop("run_speed", 1, "运行速度", "int", operators=["set"]),
                        _prop("run_speed_rdy", True, "是否支持运行速度", "boolean"),
                        _prop("li", 1, "指示灯开关", "int", operators=["set"]),
                    ],
                }
            ],
        }
    )


def test_wireless_switch_channel_l_property_does_not_project_light() -> None:
    """无线开关通道含 l，但组件品类是 relay_switch，不能生成 light."""
    device = _wireless_switch_channel_device()

    assert device["iot_category"] == "relay_switch"
    assert device["ha_platform"] == "switch"
    assert device["ha_platform_candidates"] == ["switch", "binary_sensor"]
    assert project_lights(device, domain=DOMAIN) == []
    assert not any(platform == "light" for platform, _component in _candidates(device))


def test_wireless_switch_channel_config_props_stay_as_device_controls() -> None:
    """无线开关通道的 l/run_speed/slisaon/li 应保留为配置类辅助控件."""
    device = _wireless_switch_channel_device()

    numbers = {item.prop_id: item for item in project_number_controls(device, domain=DOMAIN)}
    selects = {item.prop_id: item for item in project_select_controls(device, domain=DOMAIN)}
    switches = {item.prop_id: item for item in project_switch_controls(device, domain=DOMAIN)}
    candidates = _candidates(device)

    assert set(numbers) == {"l", "run_speed"}
    assert set(selects) == {"slisaon"}
    assert set(switches) == {"li"}
    assert numbers["l"].name == "第 1 键 亮度"
    assert numbers["l"].control_key == "1-l"
    assert numbers["l"].entity_category is None
    assert numbers["run_speed"].entity_category == "config"
    assert selects["slisaon"].entity_category == "config"
    assert switches["li"].entity_category == "config"
    assert ("number", "switch_1_l_number") in candidates
    assert ("number", "switch_1_run_speed_number") in candidates
    assert ("select", "switch_1_slisaon_select") in candidates
    assert ("switch", "switch_1_li_switch") in candidates
