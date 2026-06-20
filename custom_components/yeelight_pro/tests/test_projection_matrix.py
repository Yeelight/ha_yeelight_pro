"""Yeelight IoT 核心品类到 Home Assistant 投影矩阵回归测试."""
from __future__ import annotations

from homeassistant.components.climate import HVACMode
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.light import ColorMode

from custom_components.yeelight_pro.projector.climate import project_climate
from custom_components.yeelight_pro.projector.cover import project_cover, project_covers
from custom_components.yeelight_pro.projector.light import project_light
from custom_components.yeelight_pro.projector.light import project_lights
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
    assert projection.color_temp_kelvin == 4000
    assert projection.rgb_color == (0x33, 0x66, 0x99)
    assert projection.supported_color_modes == {ColorMode.COLOR_TEMP, ColorMode.RGB}
    assert project_switches(device, domain=DOMAIN) == []


def test_light_projection_ambiguous_modes_do_not_default_to_rgb() -> None:
    """无当前颜色状态证据时，多模式灯应优先显示色温而不是 RGB 调色盘。"""
    device = projection_payload(
        device_id="dual-mode-light-1",
        category="light",
        component_id="main_light",
        state={"p": True, "l": 80},
        component_category="color temperature light",
        properties=("p", "l", "ct", "c"),
    )

    projection = project_light(device, domain=DOMAIN)

    assert projection is not None
    assert projection.supported_color_modes == {ColorMode.COLOR_TEMP, ColorMode.RGB}
    assert projection.color_mode == ColorMode.COLOR_TEMP


def test_light_projection_product_type_does_not_override_state_capabilities() -> None:
    """已有真实状态能力时，legacy product_type 不应额外注入 RGB 能力。"""
    device = projection_payload(
        device_id="ct-product-type-legacy-1",
        category="light",
        component_id="main_light",
        state={"p": True, "l": 80, "ct": 3000},
        component_category="color temperature light",
        product_type=4,
    )

    projection = project_light(device, domain=DOMAIN)

    assert projection is not None
    assert projection.color_temp == 333
    assert projection.color_temp_kelvin == 3000
    assert projection.supported_color_modes == {ColorMode.COLOR_TEMP}
    assert projection.color_mode == ColorMode.COLOR_TEMP


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


def test_multi_switch_light_components_use_channel_names_not_generic_names() -> None:
    """私有部署缺 product schema 时，多路开关灯不能都显示为“开关灯”."""
    device = projection_payload(
        device_id="panel-light-1",
        category="light",
        component_id="light_1",
        state={"p": True},
        params={"1-p": True, "2-p": False},
        component_category="switch light",
        properties=("p",),
    )
    device["ha_device_instance"]["components"][0]["name"] = "switch light"
    device["ha_device_instance"]["components"].append({
        "component_id": "light_2",
        "name": "switch light",
        "desc": "开关灯",
        "category": "switch light",
        "available": True,
        "state": {"p": False},
    })
    device["ha_product_model"]["components"][0]["name"] = "switch light"
    device["ha_product_model"]["components"].append({
        "component_id": "light_2",
        "name": "switch light",
        "desc": "开关灯",
        "category": "switch light",
        "properties": [{"prop_id": "p", "access": "read_write"}],
        "events": [],
    })
    device["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "light_1": {"p": "1-p"},
            "light_2": {"p": "2-p"},
        }
    }

    projections = project_lights(device, domain=DOMAIN)

    assert [(item.component_id, item.name, item.power_key) for item in projections] == [
        ("light_1", "回路 1", "1-p"),
        ("light_2", "回路 2", "2-p"),
    ]


def test_multi_lights_localize_schema_technical_names_without_desc() -> None:
    """多路灯只有英文 schema 技术名时，也不能把原始英文暴露给用户."""
    device = projection_payload(
        device_id="mixed-light-1",
        category="light",
        component_id="light_1",
        state={"p": True, "l": 80, "ct": 4000},
        params={
            "1-p": True,
            "1-l": 80,
            "1-ct": 4000,
            "2-p": False,
            "2-l": 30,
            "2-c": 0x336699,
        },
        component_category="color temperature light",
        properties=("p", "l", "ct"),
    )
    device["ha_device_instance"]["components"][0]["name"] = "color temperature light"
    device["ha_device_instance"]["components"].append({
        "component_id": "light_2",
        "name": "color_light",
        "category": "color light",
        "available": True,
        "state": {"p": False, "l": 30, "c": 0x336699},
    })
    device["ha_product_model"]["components"][0]["name"] = "color temperature light"
    device["ha_product_model"]["components"].append({
        "component_id": "light_2",
        "name": "color_light",
        "category": "color light",
        "properties": [
            {"prop_id": "p", "access": "read_write"},
            {"prop_id": "l", "access": "read_write"},
            {"prop_id": "c", "access": "read_write"},
        ],
        "events": [],
    })
    device["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "light_1": {"p": "1-p", "l": "1-l", "ct": "1-ct"},
            "light_2": {"p": "2-p", "l": "2-l", "c": "2-c"},
        }
    }

    projections = project_lights(device, domain=DOMAIN)

    assert [(item.component_id, item.name) for item in projections] == [
        ("light_1", "色温灯"),
        ("light_2", "彩光灯"),
    ]


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
