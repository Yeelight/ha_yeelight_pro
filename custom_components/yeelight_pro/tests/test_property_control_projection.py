"""Writable property control projection tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.const import EntityCategory

from custom_components.yeelight_pro.number import YeelightProDeviceNumber
from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)
from custom_components.yeelight_pro.select import YeelightProDeviceSelect

from .projection_helpers import DOMAIN, projection_payload


def _property_control_payload() -> dict:
    """Build a schema-aware payload with auxiliary writable controls."""
    payload = projection_payload(
        device_id="curtain-1",
        category="curtain",
        component_id="curtain_1",
        component_category="curtain",
        state={
            "tp": 40,
            "li": 1,
            "rd": "0",
        },
        params={
            "1-tp": 40,
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
            "prop_id": "li",
            "name": "指示灯",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 0, "max": 100, "step": 1},
            "unit": "%",
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
    assert projection.unique_id == "yeelight_pro_curtain-1_curtain_1_li_number"
    assert projection.component_id == "curtain_1_li_number"
    assert projection.name == "左键 指示灯"
    assert projection.value == 1
    assert projection.native_range.min == 0
    assert projection.native_range.max == 100
    assert projection.native_range.step == 1
    assert projection.unit == "%"
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
        "component_state_keys": {"1": {"li": "1-li"}}
    }

    projection = project_number_controls(payload, domain=DOMAIN)[0]

    assert projection.component_id == "1_li_number"
    assert projection.name == "左键 指示灯"
    assert projection.control_key == "1-li"


def test_writable_value_list_projects_device_select_control() -> None:
    """非主实体占用的可写 valueList 属性应投影为设备级 select."""
    projections = project_select_controls(_property_control_payload(), domain=DOMAIN)

    assert len(projections) == 1
    projection = projections[0]
    assert projection.unique_id == "yeelight_pro_curtain-1_curtain_1_rd_select"
    assert projection.component_id == "curtain_1_rd_select"
    assert projection.name == "左键 电机方向"
    assert [(item.value, item.label) for item in projection.options] == [
        ("0", "正向"),
        ("1", "反向"),
    ]
    assert projection.value == "0"
    assert projection.control_key == "1-rd"
    assert projection.entity_category == "config"


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

    assert {item.prop_id for item in numbers} == {"li"}
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
    assert projection.name == "左键 空调遥控器"
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
    assert projection.name == "左键 背光"
    assert projection.is_on is False
    assert projection.control_key == "1-blp"


@pytest.mark.asyncio
async def test_device_number_write_sends_indexed_control_key(mock_coordinator) -> None:
    """设备级 number 写入应下发 schema control key."""
    mock_coordinator.get_device.return_value = _property_control_payload()
    mock_coordinator.async_control_device = AsyncMock()
    number = YeelightProDeviceNumber(
        mock_coordinator,
        12345,
        component_id="curtain_1_li_number",
    )

    assert number.name == "左键 指示灯"
    assert number.native_value == 1
    assert number.entity_category == EntityCategory.CONFIG

    await number.async_set_native_value(30)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"1-li": 30},
    )


@pytest.mark.asyncio
async def test_device_select_write_sends_raw_option_code(mock_coordinator) -> None:
    """设备级 select 选择标签后应下发对应 raw code."""
    mock_coordinator.get_device.return_value = _property_control_payload()
    mock_coordinator.async_control_device = AsyncMock()
    select = YeelightProDeviceSelect(
        mock_coordinator,
        12345,
        component_id="curtain_1_rd_select",
    )

    assert select.options == ["正向", "反向"]
    assert select.current_option == "正向"
    assert select.entity_category == EntityCategory.CONFIG

    await select.async_select_option("反向")

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"1-rd": "1"},
    )
