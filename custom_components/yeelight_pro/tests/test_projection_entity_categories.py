"""Yeelight IoT 实体分类投影回归测试."""

from __future__ import annotations

from homeassistant.const import EntityCategory

from custom_components.yeelight_pro.binary_sensor import YeelightProBinarySensor
from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches
from custom_components.yeelight_pro.sensor import YeelightProSensor

from .projection_helpers import DOMAIN, projection_payload


def test_sensor_entity_exposes_ha_entity_category(mock_coordinator) -> None:
    """平台实体应把投影分类转换为 HA EntityCategory。"""
    mock_coordinator.hide_unknown_entities = True
    mock_coordinator.get_device.return_value = projection_payload(
        device_id="battery-ha-1",
        category="contact_sensor",
        component_id="battery",
        state={"bl": 86},
        component_category="battery",
    )

    sensor = YeelightProSensor(mock_coordinator, 12345, component_id="battery")

    assert sensor.entity_category == EntityCategory.DIAGNOSTIC


def test_sensor_entity_handles_missing_device_payload(mock_coordinator) -> None:
    """设备拓扑短暂缺失时 sensor 不能向 projector 传 None."""
    mock_coordinator.hide_unknown_entities = True
    mock_coordinator.get_device.return_value = None

    sensor = YeelightProSensor(mock_coordinator, 12345, component_id="battery")

    assert sensor.available is False
    assert sensor.native_value is None
    assert sensor.entity_category is None


def test_binary_sensor_entity_exposes_ha_entity_category(mock_coordinator) -> None:
    """二态诊断实体也应进入 HA 诊断分组。"""
    mock_coordinator.get_device.return_value = projection_payload(
        device_id="battery-ha-2",
        category="contact_sensor",
        component_id="battery",
        state={"bcg": True},
        component_category="battery",
    )

    sensor = YeelightProBinarySensor(
        mock_coordinator,
        12345,
        component_id="battery_charging",
    )

    assert sensor.entity_category == EntityCategory.DIAGNOSTIC


def test_binary_sensor_entity_handles_missing_device_payload(mock_coordinator) -> None:
    """设备拓扑短暂缺失时 binary_sensor 不能向 projector 传 None."""
    mock_coordinator.get_device.return_value = None

    sensor = YeelightProBinarySensor(
        mock_coordinator,
        12345,
        component_id="battery_charging",
    )

    assert sensor.available is False
    assert sensor.is_on is None
    assert sensor.entity_category is None


def test_battery_component_projects_charging_binary_diagnostics() -> None:
    """电池充电状态应作为诊断类 binary_sensor 暴露."""
    device = projection_payload(
        device_id="battery-1",
        category="contact_sensor",
        component_id="battery",
        state={"bc": True, "bcg": False},
        component_category="battery",
    )

    projections = project_binary_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in projections}

    assert set(by_component) == {"battery_chargeable", "battery_charging"}
    assert by_component["battery_chargeable"].is_on is True
    assert by_component["battery_chargeable"].entity_category == "diagnostic"
    assert by_component["battery_charging"].is_on is False
    assert by_component["battery_charging"].device_class == "battery_charging"
    assert by_component["battery_charging"].entity_category == "diagnostic"


def test_gateway_properties_project_diagnostic_sensors_only() -> None:
    """网关只暴露运行诊断，不生成主控制实体."""
    device = projection_payload(
        device_id="gateway-1",
        category="gateway",
        component_id="gateway",
        state={"fm": 9584, "lf": 113924, "pl": 1, "cpt": 3, "lc": 1, "li": 0},
        component_category="gateway",
    )

    sensors = project_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in sensors}

    assert set(by_component) == {
        "connectivity_protocol",
        "free_memory",
        "indicator_switch",
        "lan_control",
        "physical_link",
        "uptime",
    }
    assert by_component["free_memory"].native_value == 9584
    assert by_component["free_memory"].entity_category == "diagnostic"
    assert by_component["uptime"].entity_category == "diagnostic"
    assert by_component["physical_link"].entity_category == "diagnostic"
    assert by_component["connectivity_protocol"].entity_category == "diagnostic"
    assert by_component["lan_control"].entity_category == "config"
    assert by_component["indicator_switch"].entity_category == "config"
    assert project_switches(device, domain=DOMAIN) == []


def test_config_properties_project_as_config_sensors_without_write_controls() -> None:
    """值域不完整的配置属性先只读展示，不能生成泛化控制实体."""
    device = projection_payload(
        device_id="dali-config-1",
        category="scene_panel",
        component_id="dali_scene_button",
        state={"ep": 2, "st": 300, "rt": 5},
        component_category="dali scene control button",
    )

    sensors = project_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in sensors}

    assert set(by_component) == {"event_priority", "repeat_timer", "short_timer"}
    assert {item.entity_category for item in sensors} == {"config"}
    assert project_switches(device, domain=DOMAIN) == []


def test_dali_energy_projects_runtime_diagnostic_sensors() -> None:
    """dali能量组件应投影为只读运行诊断实体。"""
    device = projection_payload(
        device_id="dali-energy-1",
        category="other",
        component_id="dali_energy",
        state={
            "ap": 19,
            "ae": 880,
            "ot": 3600,
            "sys_s": 2,
            "esv": 2200,
            "esvf": 50,
            "temp": 31,
            "ocp": 80,
            "lsot": 1800,
            "lsv": 360,
            "lsc": 700,
            "pf": 95,
        },
        component_category="dali energy",
    )

    projections = project_sensors(device, domain=DOMAIN)
    by_component = {projection.component_id: projection for projection in projections}

    assert set(by_component) == {
        "active_energy",
        "active_power",
        "external_supply_frequency",
        "external_supply_voltage",
        "internal_temperature",
        "light_source_current",
        "light_source_on_time",
        "light_source_voltage",
        "operating_time",
        "output_current_percent",
        "power_factor",
        "system_starts",
    }
    assert by_component["active_power"].native_value == 19
    assert by_component["active_power"].device_class == "power"
    assert by_component["active_power"].native_unit_of_measurement == "W"
    assert by_component["active_power"].state_class == "measurement"
    assert by_component["active_energy"].native_value == 880
    assert by_component["active_energy"].device_class == "energy"
    assert by_component["active_energy"].native_unit_of_measurement == "Wh"
    assert by_component["active_energy"].state_class == "total_increasing"
    assert by_component["active_power"].entity_category == "diagnostic"
    assert by_component["operating_time"].native_value == 3600
    assert by_component["operating_time"].entity_category == "diagnostic"
