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


def test_state_projectors_use_top_level_fallback_device_info() -> None:
    """无 canonical 实例时，sensor/switch 仍应归属到源设备 metadata。"""
    sensor_payload = {
        "device_id": "304784334",
        "type": "light_sensor",
        "category": "light_sensor",
        "online": True,
        "params": {"luminance": 321},
        "device_info": {
            "identifiers": [[DOMAIN, "304784334"]],
            "manufacturer": "Yeelight",
            "model": "light_sensor",
            "model_id": "YL-202",
            "name": "门厅照度",
            "suggested_area": "门厅",
        },
    }
    switch_payload = {
        "device_id": "304784336",
        "type": "switch",
        "category": "relay_switch",
        "online": True,
        "params": {"p": True},
        "device_info": {
            "identifiers": [[DOMAIN, "304784336"]],
            "manufacturer": "Yeelight",
            "model": "relay_switch",
            "model_id": "YL-201",
            "name": "墙壁开关1",
            "suggested_area": "客厅",
        },
    }

    sensor = project_sensors(sensor_payload, domain=DOMAIN)[0]
    switch = project_switches(switch_payload, domain=DOMAIN)[0]

    assert sensor.device_info is not None
    assert sensor.device_info["name"] == "门厅照度"
    assert sensor.device_info["identifiers"] == {(DOMAIN, "304784334")}
    assert sensor.device_info["suggested_area"] == "门厅"
    assert switch.device_info is not None
    assert switch.device_info["name"] == "墙壁开关1"
    assert switch.device_info["identifiers"] == {(DOMAIN, "304784336")}
    assert switch.device_info["suggested_area"] == "客厅"


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


def test_contact_sensor_projects_battery_sensor_alongside_binary_state() -> None:
    """电池类只读属性应作为独立 sensor 暴露，不能被主 binary_sensor 吞掉."""
    device = projection_payload(
        device_id="contact-battery-1",
        category="contact_sensor",
        component_id="contact_sensor",
        state={"dc": False, "alm": False, "bl": 86},
        component_category="contact sensor",
    )

    sensors = project_sensors(device, domain=DOMAIN)

    assert [(item.component_id, item.native_value) for item in sensors] == [
        ("battery", 86),
    ]
    assert sensors[0].device_class == "battery"
    assert sensors[0].native_unit_of_measurement == "%"
    assert sensors[0].entity_category == "diagnostic"


def test_temperature_humidity_payload_projects_two_sensors() -> None:
    """温湿度类运行时 payload 应按属性生成温度和湿度实体."""
    device = projection_payload(
        device_id="temp-humidity-1",
        category="other",
        component_id="temp_humidity",
        state={"t": 24.5, "h": 58},
        component_category="temperature humidity sensor",
    )

    sensors = project_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in sensors}

    assert set(by_component) == {"temperature", "humidity"}
    assert by_component["temperature"].native_value == 24.5
    assert by_component["temperature"].device_class == "temperature"
    assert by_component["humidity"].native_value == 58
    assert by_component["humidity"].device_class == "humidity"


def test_sensor_schema_projects_unknown_entity_without_runtime_value() -> None:
    """传感类 schema 暂无当前值时仍声明实体，状态交给 HA 显示 unknown."""
    device = projection_payload(
        device_id="temp-humidity-empty",
        category="other",
        component_id="temp_humidity",
        state={},
        component_category="temperature humidity sensor",
        properties=("t", "h"),
    )

    sensors = project_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in sensors}

    assert set(by_component) == {"temperature", "humidity"}
    assert by_component["temperature"].available is True
    assert by_component["temperature"].native_value is None
    assert by_component["temperature"].device_class == "temperature"
    assert by_component["humidity"].available is True
    assert by_component["humidity"].native_value is None
    assert by_component["humidity"].device_class == "humidity"


def test_multi_component_sensor_properties_keep_component_scope() -> None:
    """同设备多组件同属性不能互相覆盖，否则 HA 设备页会少实体."""
    device = projection_payload(
        device_id="dual-lux",
        category="other",
        component_id="sensor_1",
        state={"luminance": 120},
        component_category="ambient light sensor",
        properties=("luminance",),
    )
    device["ha_device_instance"]["components"].append({
        "component_id": "sensor_2",
        "name": "右侧",
        "desc": "右侧",
        "category": "ambient light sensor",
        "available": True,
        "state": {"luminance": 240},
    })
    device["ha_product_model"]["components"].append({
        "component_id": "sensor_2",
        "name": "右侧",
        "desc": "右侧",
        "category": "ambient light sensor",
        "properties": [{"prop_id": "luminance", "access": "read"}],
        "events": [],
    })
    device["ha_device_instance"]["components"][0]["name"] = "左侧"
    device["ha_device_instance"]["components"][0]["desc"] = "左侧"
    device["ha_product_model"]["components"][0]["name"] = "左侧"
    device["ha_product_model"]["components"][0]["desc"] = "左侧"

    sensors = project_sensors(device, domain=DOMAIN)

    assert [
        (item.component_id, item.unique_id, item.name, item.native_value)
        for item in sensors
    ] == [
        ("sensor_1_illuminance", "yeelight_pro_dual-lux_sensor_1_illuminance", "左侧 光照", 120),
        ("sensor_2_illuminance", "yeelight_pro_dual-lux_sensor_2_illuminance", "右侧 光照", 240),
    ]


def test_binary_sensor_schema_projects_unknown_entity_without_runtime_value() -> None:
    """二态传感 schema 暂无当前值时仍声明实体，状态交给 HA 显示 unknown。"""
    device = projection_payload(
        device_id="human-empty",
        category="human_sensor",
        component_id="human_sensor",
        state={},
        component_category="human detection sensor",
        properties=("mv", "alm"),
    )

    sensors = project_binary_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in sensors}

    assert set(by_component) == {"motion", "tamper"}
    assert by_component["motion"].available is True
    assert by_component["motion"].is_on is None
    assert by_component["motion"].device_class == "motion"
    assert by_component["tamper"].available is True
    assert by_component["tamper"].is_on is None
    assert by_component["tamper"].device_class == "tamper"


def test_multi_component_binary_sensor_properties_keep_component_scope() -> None:
    """同设备多个人感组件都应生成 binary_sensor，而不是只保留一个 motion."""
    device = projection_payload(
        device_id="dual-motion",
        category="human_sensor",
        component_id="human_1",
        state={"mv": True},
        component_category="human detection sensor",
        properties=("mv",),
    )
    device["ha_device_instance"]["components"].append({
        "component_id": "human_2",
        "name": "右侧",
        "desc": "右侧",
        "category": "human detection sensor",
        "available": True,
        "state": {"mv": False},
    })
    device["ha_product_model"]["components"].append({
        "component_id": "human_2",
        "name": "右侧",
        "desc": "右侧",
        "category": "human detection sensor",
        "properties": [{"prop_id": "mv", "access": "read"}],
        "events": [],
    })
    device["ha_device_instance"]["components"][0]["name"] = "左侧"
    device["ha_device_instance"]["components"][0]["desc"] = "左侧"
    device["ha_product_model"]["components"][0]["name"] = "左侧"
    device["ha_product_model"]["components"][0]["desc"] = "左侧"

    sensors = project_binary_sensors(device, domain=DOMAIN)

    assert [
        (item.component_id, item.unique_id, item.name, item.is_on)
        for item in sensors
    ] == [
        ("human_1_motion", "yeelight_pro_dual-motion_human_1_motion", "左侧 人体移动", True),
        ("human_2_motion", "yeelight_pro_dual-motion_human_2_motion", "右侧 人体移动", False),
    ]


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
