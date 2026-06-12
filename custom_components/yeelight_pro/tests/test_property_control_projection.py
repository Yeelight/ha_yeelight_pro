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
            "li": 1,
            "rd": "0",
        },
        params={
            "1-tp": 40,
            "1-tra": 120,
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
    assert projection.unique_id == "yeelight_pro_curtain-1_curtain_1_tra_number"
    assert projection.component_id == "curtain_1_tra_number"
    assert projection.name == "按键 1 目标旋转角度"
    assert projection.value == 120
    assert projection.native_range.min == 0
    assert projection.native_range.max == 180
    assert projection.native_range.step == 1
    assert projection.unit == "°"
    assert projection.control_key == "1-tra"
    assert projection.entity_category is None


def test_indicator_switch_projects_device_switch_not_number() -> None:
    """li 是文档中的指示灯开关，不应被错误暴露为 0-100 number."""
    payload = _property_control_payload()

    numbers = project_number_controls(payload, domain=DOMAIN)
    switches = project_switch_controls(payload, domain=DOMAIN)

    assert {item.prop_id for item in numbers} == {"tra"}
    assert len(switches) == 1
    projection = switches[0]
    assert projection.unique_id == "yeelight_pro_curtain-1_curtain_1_li_switch"
    assert projection.component_id == "curtain_1_li_switch"
    assert projection.name == "按键 1 指示灯"
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
        "component_state_keys": {"1": {"tra": "1-tra"}}
    }

    projection = project_number_controls(payload, domain=DOMAIN)[0]

    assert projection.component_id == "1_tra_number"
    assert projection.name == "按键 1 目标旋转角度"
    assert projection.control_key == "1-tra"


def test_writable_value_list_projects_device_select_control() -> None:
    """非主实体占用的可写 valueList 属性应投影为设备级 select."""
    projections = project_select_controls(_property_control_payload(), domain=DOMAIN)

    assert len(projections) == 1
    projection = projections[0]
    assert projection.unique_id == "yeelight_pro_curtain-1_curtain_1_rd_select"
    assert projection.component_id == "curtain_1_rd_select"
    assert projection.name == "按键 1 电机方向"
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

    assert {item.prop_id for item in numbers} == {"tra"}
    assert {item.prop_id for item in selects} == {"rd"}


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
    assert projection.name == "按键 1 空调遥控器"
    assert projection.is_on is True
    assert projection.control_key == "1-acrc"
    assert projection.icon == "mdi:remote"
    assert projection.entity_category == "config"


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
    assert projection.name == "按键 1 背光"
    assert projection.is_on is False
    assert projection.control_key == "1-blp"


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
