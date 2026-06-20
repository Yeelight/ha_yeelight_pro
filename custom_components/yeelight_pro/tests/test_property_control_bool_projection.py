"""Writable bool property control projection tests."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)

from .projection_helpers import DOMAIN, projection_payload


def test_writable_bool_config_projects_device_switch_control() -> None:
    """acrc 等文档支撑的布尔配置属性应出现在 HA 配置开关中."""
    payload = projection_payload(
        device_id="climate-1",
        category="temp_control",
        component_id="air_conditioner_1",
        component_category="air_conditioner",
        state={"acp": True, "acrc": True},
        params={"1-acp": True, "1-acrc": True},
    )
    payload["name"] = "浴霸双键开关"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "acp",
            "name": "空调开关",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        },
        {
            "prop_id": "acrc",
            "name": "空调遥控器",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        },
    ]
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "air_conditioner_1": {
                "acp": "1-acp",
                "acrc": "1-acrc",
            }
        }
    }

    projections = project_switch_controls(payload, domain=DOMAIN)

    assert len(projections) == 1
    projection = projections[0]
    assert projection.unique_id == "yeelight_pro_climate-1_air_conditioner_1_acrc_switch"
    assert projection.component_id == "air_conditioner_1_acrc_switch"
    assert projection.name == "空调控制器 空调遥控器"
    assert projection.is_on is True
    assert projection.control_key == "1-acrc"
    assert projection.icon == "mdi:remote"
    assert projection.entity_category == "config"


def test_climate_main_properties_do_not_project_duplicate_auxiliary_controls() -> None:
    """温控主实体已消费的 acm/acf/actt/acdfltr 不应重复成为 helper."""
    payload = projection_payload(
        device_id="multi-climate-aux-1",
        category="temp_control",
        component_id="air_conditioner_1",
        component_category="air_conditioner",
        state={
            "acp": True,
            "acm": 1,
            "acf": 4,
            "actt": 26,
            "acct": 24,
            "acdfltr": 80,
        },
        params={
            "1-acp": True,
            "1-acm": 1,
            "1-acf": 4,
            "1-actt": 26,
            "1-acct": 24,
            "1-acdfltr": 80,
            "1-acrc": True,
        },
    )
    payload["ha_product_model"]["components"][0]["properties"] = [
        {"prop_id": "acp", "access": "read_write", "property_type": "bool", "format": "bool"},
        {
            "prop_id": "acm",
            "access": "read_write",
            "property_type": "enum",
            "value_list": [{"code": "1", "desc": "制冷"}],
        },
        {
            "prop_id": "acf",
            "access": "read_write",
            "property_type": "enum",
            "value_list": [{"code": "4", "desc": "低"}],
        },
        {
            "prop_id": "actt",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 16, "max": 32, "step": 1},
        },
        {
            "prop_id": "acdfltr",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 0, "max": 255, "step": 1},
        },
        {"prop_id": "acct", "access": "read_only", "property_type": "int"},
        {"prop_id": "acrc", "access": "read_write", "property_type": "bool", "format": "bool"},
    ]
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "air_conditioner_1": {
                "acp": "1-acp",
                "acm": "1-acm",
                "acf": "1-acf",
                "actt": "1-actt",
                "acct": "1-acct",
                "acdfltr": "1-acdfltr",
                "acrc": "1-acrc",
            }
        }
    }

    assert project_number_controls(payload, domain=DOMAIN) == []
    assert project_select_controls(payload, domain=DOMAIN) == []
    assert [item.prop_id for item in project_switch_controls(payload, domain=DOMAIN)] == [
        "acrc"
    ]


def test_writable_auxiliary_bool_schema_projects_switch_control() -> None:
    """非主实体占用的可写布尔属性应按 HA switch 暴露为配置控制."""
    payload = projection_payload(
        device_id="sensor-1",
        category="human_sensor",
        component_id="human_sensor_1",
        component_category="human illuminance sensor",
        state={"mv": True, "blp": False},
        params={"1-mv": True, "1-blp": False},
    )
    payload["name"] = "传感器双键面板"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mv",
            "name": "人体移动",
            "access": "read_only",
            "property_type": "bool",
            "format": "bool",
        },
        {
            "prop_id": "blp",
            "name": "背光",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        },
    ]
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {"human_sensor_1": {"mv": "1-mv", "blp": "1-blp"}}
    }

    projections = project_switch_controls(payload, domain=DOMAIN)

    assert len(projections) == 1
    projection = projections[0]
    assert projection.component_id == "human_sensor_1_blp_switch"
    assert projection.name == "人体传感器 背光"
    assert projection.is_on is False
    assert projection.control_key == "1-blp"


def test_generic_switch_component_label_is_not_prefixed_to_auxiliary_control() -> None:
    """S21 等开关组件的配置实体不应显示英文通用 switch 前缀."""
    payload = projection_payload(
        device_id="s21-single-1",
        category="relay_switch",
        component_id="switch",
        component_category="relay_switch",
        state={"p": True, "blp": True},
        params={"p": True, "blp": True},
    )
    payload["name"] = "S21 智能墙壁开关"
    payload["ha_product_model"]["components"][0]["name"] = "switch"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "p",
            "name": "开关",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        },
        {
            "prop_id": "blp",
            "name": "面板背光开关状态",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        },
    ]
    payload["ha_device_instance"]["components"][0]["name"] = "switch"

    projections = project_switch_controls(payload, domain=DOMAIN)

    assert len(projections) == 1
    assert projections[0].component_id == "switch_blp_switch"
    assert projections[0].name == "面板背光开关状态"


def test_registry_backed_control_labels_replace_english_spec_names() -> None:
    """产品目录属性即使用英文 full_name，也必须显示易来中文描述."""
    payload = projection_payload(
        device_id="light-1",
        category="light",
        component_id="color_light",
        component_category="color light",
        state={"p": True, "dd": 300, "bp": "1", "slisaon": "0"},
        params={"dd": 300, "bp": "1", "slisaon": "0"},
    )
    payload["name"] = "彩光灯"
    payload["ha_product_model"]["components"][0]["name"] = "彩光灯"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "p",
            "name": "power",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        },
        {
            "prop_id": "dd",
            "name": "default duration",
            "access": "read_write",
            "property_type": "config",
            "format": "int",
            "value_range": {"min": 0, "max": 10000, "step": 100},
            "unit": "ms",
        },
        {
            "prop_id": "bp",
            "name": "power on boot",
            "access": "read_write",
            "property_type": "config",
            "format": "int",
            "value_list": [
                {"code": "0", "desc": "断电前状态"},
                {"code": "1", "desc": "开启"},
                {"code": "2", "desc": "关闭"},
            ],
        },
        {
            "prop_id": "slisaon",
            "name": "slisaon",
            "access": "read_write",
            "property_type": "config",
            "format": "int",
            "value_list": [
                {"code": "0", "desc": "关闭"},
                {"code": "1", "desc": "开启"},
            ],
        },
    ]
    payload["ha_device_instance"]["components"][0]["name"] = "彩光灯"

    numbers = project_number_controls(payload, domain=DOMAIN)
    selects = project_select_controls(payload, domain=DOMAIN)

    assert [item.name for item in numbers] == ["默认渐变时长"]
    assert {item.prop_id: item.name for item in selects} == {
        "bp": "上电后状态",
        "slisaon": "是否开启闪断",
    }
