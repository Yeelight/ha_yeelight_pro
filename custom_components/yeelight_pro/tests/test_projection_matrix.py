"""Yeelight IoT 核心品类到 Home Assistant 投影矩阵回归测试."""
from __future__ import annotations

from homeassistant.components.climate import HVACMode
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.light import ColorMode

from custom_components.yeelight_pro.projector.climate import project_climate
from custom_components.yeelight_pro.projector.cover import project_cover, project_covers
from custom_components.yeelight_pro.projector.light import project_light
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, projection_payload


def test_light_projection_uses_component_state_over_raw_params() -> None:
    """灯类应投影为 light，component state 优先于 raw params。"""
    device = projection_payload(
        device_id="light-1",
        category="light",
        component_id="main_light",
        state={"p": True, "l": 80, "ct": 4000, "c": 0x336699},
        params={"p": False, "l": 10},
        component_category="color temperature light",
    )

    projection = project_light(device, domain=DOMAIN)

    assert projection is not None
    assert projection.is_on is True
    assert projection.brightness == 203
    assert projection.color_temp == 250
    assert projection.rgb_color == (0x33, 0x66, 0x99)
    assert projection.supported_color_modes == {ColorMode.COLOR_TEMP, ColorMode.RGB}
    assert project_switches(device, domain=DOMAIN) == []


def test_light_projection_preserves_gateway_via_device_info() -> None:
    """子设备投影必须保留 canonical device_info 的网关父设备关系。"""
    device = projection_payload(
        device_id="light-via-gateway-1",
        category="light",
        component_id="main_light",
        state={"p": True, "l": 50},
        component_category="light",
    )
    device["ha_device_instance"]["device_info"]["via_device"] = [DOMAIN, "gateway-1"]

    projection = project_light(device, domain=DOMAIN)

    assert projection is not None
    assert projection.device_info is not None
    assert projection.device_info["via_device"] == (DOMAIN, "gateway-1")


def test_light_projection_uses_top_level_fallback_device_info() -> None:
    """旧版扁平 light payload 也必须带设备名称和型号 metadata。"""
    device = {
        "device_id": "304784333",
        "type": "light",
        "online": True,
        "params": {"p": True, "l": 80},
        "device_info": {
            "identifiers": [[DOMAIN, "304784333"]],
            "manufacturer": "Yeelight",
            "model": "light",
            "model_id": "YL-200",
            "name": "客厅筒灯 1",
            "suggested_area": "客厅",
        },
    }

    projection = project_light(device, domain=DOMAIN)

    assert projection is not None
    assert projection.device_info is not None
    assert projection.device_info["identifiers"] == {(DOMAIN, "304784333")}
    assert projection.device_info["name"] == "客厅筒灯 1"
    assert "model" not in projection.device_info
    assert projection.device_info["model_id"] == "YL-200"
    assert projection.device_info["suggested_area"] == "客厅"


def test_color_light_without_temperature_projects_rgb_without_color_temp() -> None:
    """无色温彩光灯应投影 RGB 能力，但不能暴露色温能力。"""
    device = projection_payload(
        device_id="rgb-only-light-1",
        category="light",
        component_id="main_light",
        state={"p": True, "l": 60, "c": 0x112233},
        component_category="color light without temperature",
    )

    projection = project_light(device, domain=DOMAIN)

    assert projection is not None
    assert projection.is_on is True
    assert projection.brightness == 152
    assert projection.rgb_color == (0x11, 0x22, 0x33)
    assert projection.color_temp is None
    assert projection.color_temp_range_kelvin is None
    assert projection.min_mireds is None
    assert projection.max_mireds is None
    assert projection.supported_color_modes == {ColorMode.RGB}
    assert projection.color_mode == ColorMode.RGB


def test_switch_light_component_projects_as_light() -> None:
    """switch light 是灯光组件，不应被 switch token 误排除。"""
    device = projection_payload(
        device_id="switch-light-1",
        category="light",
        component_id="switch_light",
        state={"p": True},
        component_category="switch light",
    )

    projection = project_light(device, domain=DOMAIN)

    assert projection is not None
    assert projection.component_id == "switch_light"
    assert projection.supported_color_modes == {ColorMode.ONOFF}
    assert project_switches(device, domain=DOMAIN) == []


def test_curtain_projects_cover() -> None:
    """窗帘类应投影为 cover。"""
    device = projection_payload(
        device_id="curtain-1",
        category="curtain",
        component_id="curtain",
        state={"cp": 20, "tp": 80},
        component_category="curtain",
    )

    projection = project_cover(device, domain=DOMAIN)

    assert projection is not None
    assert projection.current_cover_position == 20
    assert projection.target_cover_position == 80
    assert projection.is_opening is True
    assert projection.is_closing is False
    assert projection.device_class == CoverDeviceClass.CURTAIN


def test_multi_curtain_components_project_multiple_covers() -> None:
    """多窗帘组件应按能力拆成多个 cover，而不是只保留第一个."""
    device = projection_payload(
        device_id="curtain-dual-1",
        category="curtain",
        component_id="curtain_1",
        state={"cp": 10, "tp": 30},
        component_category="curtain",
    )
    device["params"] = {
        "1-cp": 10,
        "1-tp": 30,
        "2-cp": 90,
        "2-tp": 40,
    }
    device["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "curtain_1": {"cp": "1-cp", "tp": "1-tp"},
            "curtain_2": {"cp": "2-cp", "tp": "2-tp"},
        }
    }
    device["ha_device_instance"]["components"] = [
        {
            "component_id": "curtain_1",
            "category": "curtain",
            "available": True,
            "state": {"cp": 10, "tp": 30},
        },
        {
            "component_id": "curtain_2",
            "category": "curtain",
            "available": True,
            "state": {"cp": 90, "tp": 40},
        },
    ]
    device["ha_product_model"]["components"] = [
        {
            "component_id": "curtain_1",
            "category": "curtain",
            "name": "curtain",
            "component_type": "curtain",
            "properties": [
                {"prop_id": "cp", "access": "read"},
                {"prop_id": "tp", "access": "read_write"},
            ],
            "events": [],
        },
        {
            "component_id": "curtain_2",
            "category": "curtain",
            "name": "curtain",
            "component_type": "curtain",
            "properties": [
                {"prop_id": "cp", "access": "read"},
                {"prop_id": "tp", "access": "read_write"},
            ],
            "events": [],
        },
    ]

    projections = project_covers(device, domain=DOMAIN)

    assert [(item.component_id, item.current_cover_position) for item in projections] == [
        ("curtain_1", 10),
        ("curtain_2", 90),
    ]
    assert [item.unique_id for item in projections] == [
        "yeelight_pro_curtain-dual-1_curtain_1",
        "yeelight_pro_curtain-dual-1_curtain_2",
    ]
    assert [item.target_position_key for item in projections] == ["1-tp", "2-tp"]
    first_cover = project_cover(device, domain=DOMAIN)
    assert first_cover is not None
    assert first_cover.component_id == "curtain_1"


def test_temp_control_projects_climate() -> None:
    """温控类应投影为 climate。"""
    device = projection_payload(
        device_id="climate-1",
        category="temp_control",
        component_id="air_conditioner",
        state={"acp": True, "aco": True, "acct": 24, "actt": 26},
        component_category="air_conditioner",
    )

    projection = project_climate(device, domain=DOMAIN)

    assert projection is not None
    assert projection.current_temperature == 24
    assert projection.target_temperature == 26
    assert projection.hvac_mode == HVACMode.AUTO


def test_relay_switch_projects_switch() -> None:
    """继电器开关类应投影为 switch。"""
    device = projection_payload(
        device_id="switch-1",
        category="relay_switch",
        component_id="switch_control",
        state={"p": True},
        component_category="switch control",
    )

    projections = project_switches(device, domain=DOMAIN)

    assert len(projections) == 1
    assert projections[0].component_id == "switch_control"
    assert projections[0].control_key == "p"
    assert projections[0].is_on is True
