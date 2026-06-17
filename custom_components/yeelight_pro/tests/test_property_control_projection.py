"""Writable property control projection tests."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)

from .projection_helpers import DOMAIN, projection_payload


def _property_control_payload() -> dict:
    """Build a schema-aware payload with auxiliary writable controls."""
    payload = projection_payload(
        device_id="curtain-1",
        category="curtain",
        component_id="curtain_1",
        component_category="zebra blinds",
        state={
            "tp": 40,
            "tra": 120,
            "rg": 4,
            "li": 1,
            "rd": "0",
        },
        params={
            "1-tp": 40,
            "1-tra": 120,
            "1-rg": 4,
            "1-li": 1,
            "1-rd": "0",
        },
    )
    payload["name"] = "厨房双键开关"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "tp",
            "name": "目标位置",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 0, "max": 100, "step": 1},
            "unit": "%",
        },
        {
            "prop_id": "tra",
            "name": "目标旋转角度",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 0, "max": 180, "step": 1},
            "unit": "°",
        },
        {
            "prop_id": "rg",
            "name": "旋转档位",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 1, "max": 10, "step": 1},
        },
        {
            "prop_id": "li",
            "name": "指示灯",
            "access": "read_write",
            "property_type": "int",
        },
        {
            "prop_id": "rd",
            "name": "电机方向",
            "access": "read_write",
            "property_type": "enum",
            "value_list": [
                {"code": "0", "desc": "正向"},
                {"code": "1", "desc": "反向"},
            ],
        },
    ]
    return payload


def test_writable_value_range_projects_device_number_control() -> None:
    """非主实体占用的可写 valueRange 属性应投影为设备级 number."""
    projections = project_number_controls(_property_control_payload(), domain=DOMAIN)

    assert len(projections) == 1
    projection = projections[0]
    assert projection.unique_id == "yeelight_pro_curtain-1_curtain_1_rg_number"
    assert projection.component_id == "curtain_1_rg_number"
    assert projection.name == "窗帘 旋转档位"
    assert projection.value == 4
    assert projection.native_range.min == 1
    assert projection.native_range.max == 10
    assert projection.native_range.step == 1
    assert projection.control_key == "1-rg"
    assert projection.entity_category == "config"


def test_indicator_switch_projects_device_switch_not_number() -> None:
    """li 是文档中的指示灯开关，不应被错误暴露为 0-100 number."""
    payload = _property_control_payload()

    numbers = project_number_controls(payload, domain=DOMAIN)
    switches = project_switch_controls(payload, domain=DOMAIN)

    assert {item.prop_id for item in numbers} == {"rg"}
    assert len(switches) == 1
    projection = switches[0]
    assert projection.unique_id == "yeelight_pro_curtain-1_curtain_1_li_switch"
    assert projection.component_id == "curtain_1_li_switch"
    assert projection.name == "窗帘 指示灯"
    assert projection.is_on is True
    assert projection.on_value == 1
    assert projection.off_value == 0
    assert projection.control_key == "1-li"
    assert projection.entity_category == "config"


def test_numeric_component_id_projects_friendly_control_name() -> None:
    """易来 schema 若返回纯数字组件 ID，配置实体也应显示中文通道名."""
    payload = _property_control_payload()
    component = payload["ha_device_instance"]["components"][0]
    component["component_id"] = "1"
    component["name"] = "1"
    payload["ha_product_model"]["components"][0]["component_id"] = "1"
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {"1": {"rg": "1-rg", "tra": "1-tra"}}
    }

    projection = project_number_controls(payload, domain=DOMAIN)[0]

    assert projection.component_id == "1_rg_number"
    assert projection.name == "按键 1 旋转档位"
    assert projection.control_key == "1-rg"


def test_writable_value_list_projects_device_select_control() -> None:
    """非主实体占用的可写 valueList 属性应投影为设备级 select."""
    projections = project_select_controls(_property_control_payload(), domain=DOMAIN)

    assert len(projections) == 1
    projection = projections[0]
    assert projection.unique_id == "yeelight_pro_curtain-1_curtain_1_rd_select"
    assert projection.component_id == "curtain_1_rd_select"
    assert projection.name == "窗帘 电机方向"
    assert [(item.value, item.label) for item in projection.options] == [
        ("0", "正向"),
        ("1", "反向"),
    ]
    assert projection.value == "0"
    assert projection.control_key == "1-rd"
    assert projection.entity_category == "config"


def test_reverse_direction_uses_registry_options_when_schema_list_is_missing() -> None:
    """rd 的正反向枚举来自 Yeelight registry，schema 缺列表也应生成 select."""
    payload = _property_control_payload()
    rd_prop = next(
        prop
        for prop in payload["ha_product_model"]["components"][0]["properties"]
        if prop["prop_id"] == "rd"
    )
    rd_prop.pop("value_list")

    projections = project_select_controls(payload, domain=DOMAIN)

    assert len(projections) == 1
    projection = projections[0]
    assert projection.component_id == "curtain_1_rd_select"
    assert [(item.value, item.label) for item in projection.options] == [
        ("0", "正向"),
        ("1", "反向"),
    ]
    assert projection.value == "0"
    assert projection.control_key == "1-rd"


def test_schema_backed_auxiliary_controls_remain_available_without_read_state() -> None:
    """schema 明确可写时，缺少当前读值不应导致配置控件不可用."""
    payload = _property_control_payload()
    component = payload["ha_device_instance"]["components"][0]
    component["state"] = {}
    payload["params"] = {}

    numbers = project_number_controls(payload, domain=DOMAIN)
    selects = project_select_controls(payload, domain=DOMAIN)

    assert numbers[0].available is True
    assert numbers[0].value is None
    assert selects[0].available is True
    assert selects[0].value is None


def test_schema_backed_auxiliary_controls_ignore_empty_unavailable_component() -> None:
    """schema 存在且状态为空时，组件 available=false 不应误伤配置控件."""
    payload = _property_control_payload()
    component = payload["ha_device_instance"]["components"][0]
    component["available"] = False
    component["state"] = {}
    payload["params"] = {}

    numbers = project_number_controls(payload, domain=DOMAIN)
    selects = project_select_controls(payload, domain=DOMAIN)

    assert numbers[0].available is True
    assert selects[0].available is True


def test_auxiliary_controls_are_unavailable_when_device_is_offline() -> None:
    """设备离线时不能用 schema 规则伪装配置控件在线."""
    payload = _property_control_payload()
    payload["online"] = False
    payload["ha_device_instance"]["online"] = False
    component = payload["ha_device_instance"]["components"][0]
    component["available"] = False
    component["state"] = {}
    payload["params"] = {}

    numbers = project_number_controls(payload, domain=DOMAIN)
    selects = project_select_controls(payload, domain=DOMAIN)

    assert numbers[0].available is False
    assert selects[0].available is False


def test_main_entity_properties_are_not_projected_as_duplicate_controls() -> None:
    """主实体已消费的 tp 等属性不能重复生成 number/select."""
    numbers = project_number_controls(_property_control_payload(), domain=DOMAIN)
    selects = project_select_controls(_property_control_payload(), domain=DOMAIN)

    assert {item.prop_id for item in numbers} == {"rg"}
    assert {item.prop_id for item in selects} == {"rd"}


def test_runtime_other_music_controls_use_documented_property_names() -> None:
    """全景屏音乐组件不能把 other/raw 英文描述泄漏到实体名."""
    payload = projection_payload(
        device_id="screen-1",
        category="other",
        component_id="other",
        component_category="other",
        state={"mppm": 1, "mpmp": False},
        params={"mppm": 1, "mpmp": False},
    )
    payload["name"] = "全景屏"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mppm",
            "name": "music player play mode,音乐播放器播放模式",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 0, "max": 10, "step": 1},
        },
        {
            "prop_id": "mpmp",
            "name": "music player play pause,音乐播放器播放/暂停",
            "access": "read_write",
            "property_type": "bool",
        },
    ]

    numbers = project_number_controls(payload, domain=DOMAIN)
    switches = project_switch_controls(payload, domain=DOMAIN)

    assert numbers[0].name == "音乐播放器播放模式"
    assert switches[0].name == "音乐播放器播放/暂停"


def test_structural_component_controls_use_chinese_component_label() -> None:
    """空调等官方组件别名不能把 air_conditioner 泄漏到辅助控制实体名."""
    payload = projection_payload(
        device_id="climate-helper-1",
        category="temp_control",
        component_id="air_conditioner_1",
        component_category="air_conditioner",
        state={"acrc": False},
        params={"1-acrc": False},
    )
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "air_conditioner_1": {"acrc": "1-acrc"},
        }
    }
    payload["ha_product_model"]["components"][0]["name"] = "air conditioner"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "acrc",
            "name": "空调遥控器使能",
            "access": "read_write",
            "property_type": "bool",
        },
    ]

    switches = project_switch_controls(payload, domain=DOMAIN)

    assert switches[0].name == "空调控制器 空调遥控器使能"
