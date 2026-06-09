"""Yeelight IoT 只读状态与传感器投影回归测试."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, projection_payload


def test_contact_sensor_projects_door_binary_sensor() -> None:
    """接触式传感器应投影为 door binary_sensor。"""
    device = projection_payload(
        device_id="contact-1",
        category="contact_sensor",
        component_id="contact_sensor",
        state={"dc": True},
        component_category="contact sensor",
    )

    projections = project_binary_sensors(device, domain=DOMAIN)

    assert len(projections) == 1
    assert projections[0].component_id == "door"
    assert projections[0].device_class == "door"
    assert projections[0].is_on is False


def test_human_sensor_projects_motion_binary_sensor() -> None:
    """人体传感器应投影为 motion binary_sensor。"""
    device = projection_payload(
        device_id="human-1",
        category="human_sensor",
        component_id="human_detection",
        state={"mv": True},
        component_category="human detection sensor",
    )

    projections = project_binary_sensors(device, domain=DOMAIN)

    assert len(projections) == 1
    assert projections[0].component_id == "motion"
    assert projections[0].device_class == "motion"
    assert projections[0].is_on is True


def test_light_sensor_projects_luminance_sensor() -> None:
    """环境光传感器应投影为 illuminance sensor。"""
    device = projection_payload(
        device_id="lux-1",
        category="light_sensor",
        component_id="ambient_light_sensor",
        state={"luminance": 321},
        params={"luminance": 100},
        component_category="ambient light sensor",
    )

    projections = project_sensors(device, domain=DOMAIN)

    assert len(projections) == 1
    assert projections[0].component_id == "illuminance"
    assert projections[0].native_value == 321
    assert projections[0].device_class == "illuminance"
    assert projections[0].native_unit_of_measurement == "lx"


def test_power_meter_projects_power_and_energy_sensors() -> None:
    """电量组件应投影为只读功率和电量 sensor。"""
    device = projection_payload(
        device_id="power-1",
        category="other",
        component_id="power_meter",
        state={"curp": 18, "iec": 250},
        component_category="power meter",
    )

    projections = project_sensors(device, domain=DOMAIN)
    by_component = {projection.component_id: projection for projection in projections}

    assert set(by_component) == {"current_power", "energy_consumption"}
    assert by_component["current_power"].native_value == 18
    assert by_component["current_power"].device_class == "power"
    assert by_component["current_power"].native_unit_of_measurement == "W"
    assert by_component["energy_consumption"].native_value == 250
    assert by_component["energy_consumption"].device_class == "energy"
    assert by_component["energy_consumption"].native_unit_of_measurement == "Wh"


def test_dali_energy_projects_only_stable_power_and_energy_sensors() -> None:
    """dali能量组件首版仅投影 ap/ae，避免单位未收敛字段误导用户。"""
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

    assert set(by_component) == {"active_power", "active_energy"}
    assert by_component["active_power"].native_value == 19
    assert by_component["active_power"].device_class == "power"
    assert by_component["active_power"].native_unit_of_measurement == "W"
    assert by_component["active_power"].state_class == "measurement"
    assert by_component["active_energy"].native_value == 880
    assert by_component["active_energy"].device_class == "energy"
    assert by_component["active_energy"].native_unit_of_measurement == "Wh"
    assert by_component["active_energy"].state_class == "total_increasing"


def test_raw_params_and_component_state_merge_without_losing_unmodeled_params() -> None:
    """runtime params 未建模字段必须保留，component state 对重名字段优先。"""
    device = projection_payload(
        device_id="human-merge-1",
        category="human_sensor",
        component_id="human_sensor",
        state={"alm": False, "mv": False},
        params={"mv": True},
        component_category="human detection sensor",
    )
    projections = project_binary_sensors(device, domain=DOMAIN)
    values = {projection.component_id: projection.is_on for projection in projections}
    assert values == {"motion": False, "tamper": False}

    raw_only = projection_payload(
        device_id="human-merge-2",
        category="human_sensor",
        component_id="human_sensor",
        state={"alm": False},
        params={"mv": True},
        component_category="human detection sensor",
    )
    raw_only_values = {
        projection.component_id: projection.is_on
        for projection in project_binary_sensors(raw_only, domain=DOMAIN)
    }
    assert raw_only_values == {"motion": True, "tamper": False}


def test_other_category_degrades_to_known_sensor_only_when_properties_match() -> None:
    """other 品类不泛化生成未知实体，仅在属性明确时降级为 sensor。"""
    known = projection_payload(
        device_id="other-1",
        category="other",
        component_id="power_meter",
        state={"luminance": 12},
        component_category="power meter",
    )
    unknown = projection_payload(
        device_id="other-2",
        category="other",
        component_id="unknown_component",
        state={"vendor_private": 1},
        component_category="unknown",
    )

    assert [item.component_id for item in project_sensors(known, domain=DOMAIN)] == [
        "illuminance"
    ]
    assert project_sensors(unknown, domain=DOMAIN) == []
    assert project_switches(unknown, domain=DOMAIN) == []
