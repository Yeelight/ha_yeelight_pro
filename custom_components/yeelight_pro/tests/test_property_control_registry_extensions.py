"""Registry-backed auxiliary property projection extensions."""

from __future__ import annotations

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE

import pytest

from custom_components.yeelight_pro.climate import YeelightProClimate
from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.climate import project_climate
from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)
from custom_components.yeelight_pro.projector.sensor import project_sensors

from .projection_helpers import DOMAIN, projection_payload


def _schema_property(
    prop_id: str,
    *,
    access: str = "read_write",
    property_type: str = "int",
    name: str | None = None,
) -> dict:
    """Build a minimal product-schema property row."""
    return {
        "prop_id": prop_id,
        "name": name or prop_id,
        "access": access,
        "property_type": property_type,
    }


def _payload_with_props(*, state: dict, props: tuple[str, ...], category: str = "light") -> dict:
    """Build a schema-aware payload whose property metadata comes from registry."""
    payload = projection_payload(
        device_id="registry-extensions-1",
        category=category,
        component_id="component_1",
        component_category=category,
        state=state,
        params={f"1-{key}": value for key, value in state.items()},
    )
    payload["ha_product_model"]["components"][0]["properties"] = [
        _schema_property(prop) for prop in props
    ]
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "component_1": {prop: f"1-{prop}" for prop in props}
        }
    }
    return payload


def test_temp_control_registry_properties_split_into_selects_and_numbers() -> None:
    """温控扩展属性应按物模型枚举和值域投影为配置 select/number."""
    payload = _payload_with_props(
        category="temp_control",
        state={"bhm": "2", "do": 15, "ve": "3", "fa": "1", "he": "0", "sa": 90},
        props=("bhm", "do", "ve", "fa", "he", "sa"),
    )

    selects = {item.prop_id: item for item in project_select_controls(payload, domain=DOMAIN)}
    numbers = {item.prop_id: item for item in project_number_controls(payload, domain=DOMAIN)}

    assert set(selects) == {"bhm", "ve", "fa", "he"}
    assert [(item.value, item.label) for item in selects["bhm"].options] == [
        ("1", "干燥"),
        ("2", "除雾"),
        ("3", "快速除雾"),
        ("4", "极速加热"),
    ]
    assert [(item.value, item.label) for item in selects["ve"].options] == [
        ("0", "关闭"),
        ("1", "低档"),
        ("2", "中档"),
        ("3", "高档"),
    ]
    assert selects["bhm"].entity_category is None
    assert numbers["do"].native_range.min == 1
    assert numbers["do"].native_range.max == 120
    assert numbers["do"].unit == "min"
    assert numbers["sa"].native_range.min == 60
    assert numbers["sa"].native_range.max == 120
    assert numbers["do"].entity_category is None
    assert numbers["sa"].entity_category == "config"


def test_bath_heat_mode_excludes_read_only_other_mode_from_write_options() -> None:
    """浴霸模式 5 是只读上报态，不能作为 HA select 可写选项."""
    payload = _payload_with_props(
        category="temp_control",
        state={"bhm": "5"},
        props=("bhm",),
    )

    select = next(
        item for item in project_select_controls(payload, domain=DOMAIN) if item.prop_id == "bhm"
    )

    assert select.value == "5"
    assert [(item.value, item.label) for item in select.options] == [
        ("1", "干燥"),
        ("2", "除雾"),
        ("3", "快速除雾"),
        ("4", "极速加热"),
    ]


def test_light_and_ac_registry_config_properties_project_controls() -> None:
    """灯光和空调配置属性应进入 HA 配置控制，而不是丢为未知属性."""
    payload = _payload_with_props(
        state={
            "angle": 45,
            "dd": 2000,
            "slisaon": 1,
            "bp": "1",
            "acdfltr": 80,
        },
        props=("angle", "dd", "slisaon", "bp", "acdfltr"),
    )

    numbers = {item.prop_id: item for item in project_number_controls(payload, domain=DOMAIN)}
    selects = {item.prop_id: item for item in project_select_controls(payload, domain=DOMAIN)}

    assert numbers["angle"].native_range.max == 255
    assert numbers["dd"].native_range.max == 10000
    assert numbers["acdfltr"].native_range.max == 255
    assert numbers["angle"].entity_category == "config"
    assert numbers["dd"].entity_category == "config"
    assert numbers["acdfltr"].entity_category is None
    assert [(item.value, item.label) for item in selects["slisaon"].options] == [
        ("0", "关闭"),
        ("1", "开启"),
    ]
    assert [(item.value, item.label) for item in selects["bp"].options] == [
        ("0", "断电前状态"),
        ("1", "开启"),
        ("2", "关闭"),
    ]
    assert {item.entity_category for item in selects.values()} == {"config"}


def test_curtain_and_zebra_blind_registry_properties_project_controls() -> None:
    """窗帘/梦幻帘扩展属性应生成配置控件，tra 由 cover tilt 独占."""
    payload = _payload_with_props(
        category="curtain",
        state={
            "open_type": "1",
            "tra": 120,
            "rrd": "0",
            "rg": 4,
            "run_speed": 70,
        },
        props=("open_type", "tra", "rrd", "rg", "run_speed"),
    )

    numbers = {item.prop_id: item for item in project_number_controls(payload, domain=DOMAIN)}
    selects = {item.prop_id: item for item in project_select_controls(payload, domain=DOMAIN)}

    assert "tra" not in numbers
    assert numbers["rg"].native_range.max == 10
    assert numbers["run_speed"].native_range.max == 100
    assert set(selects) == {"open_type", "rrd"}
    assert [(item.value, item.label) for item in selects["rrd"].options] == [
        ("0", "正向"),
        ("1", "反向"),
    ]
    assert {item.entity_category for item in selects.values()} == {"config"}


def test_read_only_registry_diagnostics_project_sensors_without_unknown_fallback() -> None:
    """文档支撑的只读状态应成为诊断 sensor，不再依赖未知 fallback."""
    payload = _payload_with_props(
        category="curtain",
        state={"fv": "1.2.80", "slisaon_rdy": 1, "rs": 1, "trs": 0, "cra": 90},
        props=("fv", "slisaon_rdy", "rs", "trs", "cra"),
    )

    sensors = {item.component_id: item for item in project_sensors(payload, domain=DOMAIN)}
    binaries = {
        item.component_id: item for item in project_binary_sensors(payload, domain=DOMAIN)
    }

    assert set(sensors) == {"current_rotary_angle", "firmware_version"}
    assert set(binaries) == {"route_calibrated", "slisaon_ready", "tilt_route_calibrated"}
    assert sensors["firmware_version"].native_value == "1.2.80"
    assert sensors["current_rotary_angle"].native_unit_of_measurement == "°"
    assert {item.entity_category for item in sensors.values()} == {"diagnostic"}
    assert binaries["route_calibrated"].is_on is True
    assert binaries["tilt_route_calibrated"].is_on is False
    assert {item.entity_category for item in binaries.values()} == {"diagnostic"}


def test_registry_config_scalars_without_value_metadata_do_not_project_sensors() -> None:
    """无安全控件元数据的读写配置属性不能伪装为 sensor。"""
    payload = _payload_with_props(
        category="other",
        state={"fblck": 1, "fbnum": 3, "level_limit_rdy": 1},
        props=("fblck", "fbnum", "level_limit_rdy"),
    )

    sensors = {item.component_id: item for item in project_sensors(payload, domain=DOMAIN)}
    numbers = project_number_controls(payload, domain=DOMAIN)
    selects = project_select_controls(payload, domain=DOMAIN)
    switches = project_switch_controls(payload, domain=DOMAIN)

    assert sensors == {}
    assert numbers == []
    assert selects == []
    assert switches == []


@pytest.mark.asyncio
async def test_climate_uses_documented_power_and_target_temperature_keys(
    mock_coordinator,
) -> None:
    """climate 写入应使用实际存在的 power/target key，不能把 aco 在线状态当开关."""
    payload = projection_payload(
        device_id="climate-power-1",
        category="temp_control",
        component_id="temp_control_1",
        component_category="temp control",
        state={"p": True, "t": 24, "tgt": 26},
        params={"1-p": True, "1-tgt": 26},
    )
    payload["ha_product_model"]["components"][0]["properties"] = [
        _schema_property("p", property_type="bool"),
        _schema_property("t", access="read_only"),
        _schema_property("tgt"),
    ]
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {"temp_control_1": {"p": "1-p", "tgt": "1-tgt"}}
    }
    projection = project_climate(payload, domain=DOMAIN)
    assert projection is not None
    assert projection.power_key == "1-p"
    assert projection.target_temperature_key == "1-tgt"

    mock_coordinator.get_device.return_value = payload
    climate = YeelightProClimate(mock_coordinator, "climate-power-1")

    await climate.async_set_hvac_mode(HVACMode.OFF)
    await climate.async_set_temperature(**{ATTR_TEMPERATURE: 23})

    assert mock_coordinator.async_control_device.await_args_list == [
        (("climate-power-1", {"1-p": False}),),
        (("climate-power-1", {"1-tgt": 23.0}),),
    ]
