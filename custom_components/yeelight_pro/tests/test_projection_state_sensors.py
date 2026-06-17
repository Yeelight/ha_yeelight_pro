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


def test_climate_main_properties_do_not_project_duplicate_sensors() -> None:
    """温控主实体已表达的模式/风速/温度/导风/在线状态不应重复成 sensor."""
    device = projection_payload(
        device_id="climate-sensor-dup-1",
        category="temp_control",
        component_id="air_conditioner_1",
        state={
            "acp": True,
            "acm": 1,
            "acf": 4,
            "actt": 26,
            "acct": 24,
            "o": True,
            "acd": 30,
            "acdfltr": 80,
        },
        component_category="air_conditioner",
        properties=("acp", "acm", "acf", "actt", "acct", "o", "acd", "acdfltr"),
    )

    sensors = project_sensors(device, domain=DOMAIN)

    assert [(item.component_id, item.name, item.native_value) for item in sensors] == [
        ("ac_delay_remaining", "空调延时剩余", 30),
    ]


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


def test_documented_safe_registry_properties_project_diagnostic_sensors() -> None:
    """CSV 已知的安全标量属性应进入 HA 设备页，而不是被当作未知属性隐藏。"""
    device = projection_payload(
        device_id="gateway-diagnostics-1",
        category="gateway",
        component_id="gateway",
        state={"hb_interval": 30, "ttl": 5, "retrans": 2, "tx_power": 8},
        component_category="mesh",
        properties=("hb_interval", "ttl", "retrans", "tx_power"),
    )

    sensors = project_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in sensors}

    assert set(by_component) == {
        "heart_beat_interval",
        "retrans_num",
        "time_to_live",
        "transmit_power",
    }
    assert by_component["heart_beat_interval"].native_value == 30
    assert {item.entity_category for item in sensors} == {"diagnostic"}


def test_sensitive_or_structured_registry_properties_do_not_project_sensors() -> None:
    """凭证、地址和结构化配置即使在 CSV 中可读，也不能暴露为 HA 实体。"""
    device = projection_payload(
        device_id="sensitive-registry-1",
        category="gateway",
        component_id="gateway",
        state={
            "ip": "192.168.1.2",
            "mac": "aa:bb:cc:dd:ee:ff",
            "deviceKey": "secret",
            "psk": "secret",
            "nightMode": {"enabled": True},
        },
        component_category="wifi",
        properties=("ip", "mac", "deviceKey", "psk", "nightMode"),
    )

    assert project_sensors(device, domain=DOMAIN) == []


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
