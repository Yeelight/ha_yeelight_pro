"""Yeelight IoT 核心品类到 Home Assistant 投影矩阵回归测试."""
from __future__ import annotations

from homeassistant.components.climate import HVACMode
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.light import ColorMode

from custom_components.yeelight_pro.projector.climate import project_climate
from custom_components.yeelight_pro.projector.cover import project_cover
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


def test_temp_control_projects_climate() -> None:
    """温控类应投影为 climate。"""
    device = projection_payload(
        device_id="climate-1",
        category="temp_control",
        component_id="air_conditioner",
        state={"aco": True, "acct": 24, "actt": 26},
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
