"""Yeelight IoT schema-backed availability projection tests."""

from __future__ import annotations

from custom_components.yeelight_pro.canonical.models import (
    ComponentInstanceModel,
    HADeviceInstanceModel,
)
from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.climate import project_climate
from custom_components.yeelight_pro.projector.cover import project_cover
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.fan import project_fans
from custom_components.yeelight_pro.projector.light import project_light
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, projection_payload


def test_canonical_runtime_availability_parses_missing_and_string_values() -> None:
    """canonical 层必须保留 Open API 缺省可用语义，并正确解析字符串 false."""
    assert HADeviceInstanceModel.from_dict({"device_id": "missing"}).online is True
    assert HADeviceInstanceModel.from_dict(
        {"device_id": "null", "online": None}
    ).online is True
    assert HADeviceInstanceModel.from_dict(
        {"device_id": "down", "online": "false"}
    ).online is False
    assert ComponentInstanceModel.from_dict({"component_id": "main"}).available is True
    assert ComponentInstanceModel.from_dict(
        {"component_id": "main", "available": None}
    ).available is True
    assert ComponentInstanceModel.from_dict(
        {"component_id": "main", "available": "false"}
    ).available is False


def test_control_schema_projects_available_entity_without_runtime_value() -> None:
    """控制类 schema 暂无当前值时，实体仍应可用但状态保持未知。"""
    switch_device = projection_payload(
        device_id="switch-empty",
        category="relay_switch",
        component_id="switch_control",
        state={},
        component_category="switch control",
        properties=("p",),
    )
    cover_device = projection_payload(
        device_id="cover-empty",
        category="curtain",
        component_id="curtain",
        state={},
        component_category="curtain",
        properties=("cp", "tp"),
    )
    climate_device = projection_payload(
        device_id="climate-empty",
        category="temp_control",
        component_id="air_conditioner",
        state={},
        component_category="air_conditioner",
        properties=("aco", "actt", "acct"),
    )

    switch = project_switches(switch_device, domain=DOMAIN)[0]
    cover = project_cover(cover_device, domain=DOMAIN)
    climate = project_climate(climate_device, domain=DOMAIN)

    assert switch.available is True
    assert switch.is_on is False
    assert cover is not None
    assert cover.available is True
    assert cover.current_cover_position is None
    assert cover.target_cover_position is None
    assert climate is not None
    assert climate.available is True
    assert climate.current_temperature is None
    assert climate.target_temperature is None


def test_schema_backed_empty_state_remains_available_when_component_flag_is_false() -> None:
    """schema 已声明但本轮读值为空时，不应把组件状态稀疏误判为不可用."""
    light_device = projection_payload(
        device_id="light-empty-unavailable",
        category="light",
        component_id="main_light",
        state={},
        component_category="color temperature light",
        properties=("p", "l", "ct"),
    )
    binary_device = projection_payload(
        device_id="binary-empty-unavailable",
        category="human_sensor",
        component_id="human_sensor",
        state={},
        component_category="human detection sensor",
        properties=("mv",),
    )
    sensor_device = projection_payload(
        device_id="sensor-empty-unavailable",
        category="other",
        component_id="power_meter",
        state={},
        component_category="power meter",
        properties=("curp",),
    )
    fan_device = projection_payload(
        device_id="fan-empty-unavailable",
        category="temp_control",
        component_id="fan_1",
        state={},
        component_category="fresh air",
        properties=("vmcp", "vmcf"),
    )
    for device in (light_device, binary_device, sensor_device, fan_device):
        device["ha_device_instance"]["components"][0]["available"] = False

    light = project_light(light_device, domain=DOMAIN)
    binary = project_binary_sensors(binary_device, domain=DOMAIN)[0]
    sensor = project_sensors(sensor_device, domain=DOMAIN)[0]
    fan = project_fans(fan_device, domain=DOMAIN)[0]

    assert light is not None
    assert light.available is True
    assert binary.available is True
    assert sensor.available is True
    assert fan.available is True
    assert fan.name == "按键 1"


def test_component_unavailable_with_runtime_state_stays_unavailable() -> None:
    """组件明确带运行时状态且标记 unavailable 时，不能被 schema 规则伪装在线."""
    switch_device = projection_payload(
        device_id="switch-component-down",
        category="relay_switch",
        component_id="switch_control",
        state={"p": True},
        component_category="switch control",
        properties=("p",),
    )
    switch_device["ha_device_instance"]["components"][0]["available"] = False

    switch = project_switches(switch_device, domain=DOMAIN)[0]

    assert switch.available is False


def test_control_schema_projects_unavailable_when_device_is_offline() -> None:
    """控制类实体只有离线或组件不可用时才应显示不可用。"""
    switch_device = projection_payload(
        device_id="switch-offline",
        category="relay_switch",
        component_id="switch_control",
        state={},
        component_category="switch control",
        properties=("p",),
        online=False,
    )

    switch = project_switches(switch_device, domain=DOMAIN)[0]

    assert switch.available is False


def test_legacy_payload_missing_online_field_defaults_available() -> None:
    """Open API 缺少 online 字段时，有明确能力的 fallback 实体不应不可用."""
    light = project_light({
        "device_id": "legacy-light",
        "category": "light",
        "params": {"p": True, "l": 80},
    }, domain=DOMAIN)
    switch = project_switches({
        "device_id": "legacy-switch",
        "category": "relay_switch",
        "params": {"1-p": True},
    }, domain=DOMAIN)[0]
    sensor = project_sensors({
        "device_id": "legacy-sensor",
        "category": "other",
        "params": {"curp": 12},
    }, domain=DOMAIN)[0]
    binary = project_binary_sensors({
        "device_id": "legacy-human",
        "category": "human_sensor",
        "params": {"mv": True},
    }, domain=DOMAIN)[0]
    event = project_events({
        "device_id": "legacy-panel",
        "category": "scene_panel",
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "model-panel",
                "manufacturer": "Yeelight",
                "model": "情景面板",
                "category": "scene_panel",
            },
            "components": [
                {
                    "component_id": "scene_button",
                    "category": "scene_panel",
                    "events": [{"event_id": 1, "name": "click"}],
                }
            ],
        },
    }, domain=DOMAIN)[0]

    assert light is not None
    assert light.available is True
    assert switch.available is True
    assert sensor.available is True
    assert binary.available is True
    assert event.available is True


def test_schema_payload_null_online_defaults_available_across_platforms() -> None:
    """Open API/canonical online=null 不能让 schema 驱动实体整体不可用."""
    light_device = projection_payload(
        device_id="light-null-online",
        category="light",
        component_id="main_light",
        state={"p": True},
        component_category="color temperature light",
        properties=("p", "l", "ct"),
    )
    switch_device = projection_payload(
        device_id="switch-null-online",
        category="relay_switch",
        component_id="switch_1",
        state={"p": True},
        component_category="switch control",
        properties=("p",),
    )
    sensor_device = projection_payload(
        device_id="sensor-null-online",
        category="other",
        component_id="power_meter",
        state={"curp": 12},
        component_category="power meter",
        properties=("curp",),
    )
    cover_device = projection_payload(
        device_id="cover-null-online",
        category="curtain",
        component_id="curtain",
        state={"cp": 10},
        component_category="curtain",
        properties=("cp",),
    )
    climate_device = projection_payload(
        device_id="climate-null-online",
        category="temp_control",
        component_id="air_conditioner",
        state={"aco": True},
        component_category="air_conditioner",
        properties=("aco", "actt", "acct"),
    )
    fan_device = projection_payload(
        device_id="fan-null-online",
        category="temp_control",
        component_id="fan_1",
        state={"vmcp": True},
        component_category="fresh air",
        properties=("vmcp", "vmcf"),
    )
    for device in (
        light_device,
        switch_device,
        sensor_device,
        cover_device,
        climate_device,
        fan_device,
    ):
        device["online"] = None
        device["ha_device_instance"]["online"] = None

    light = project_light(light_device, domain=DOMAIN)
    switch = project_switches(switch_device, domain=DOMAIN)[0]
    sensor = project_sensors(sensor_device, domain=DOMAIN)[0]
    cover = project_cover(cover_device, domain=DOMAIN)
    climate = project_climate(climate_device, domain=DOMAIN)
    fan = project_fans(fan_device, domain=DOMAIN)[0]

    assert light is not None
    assert light.available is True
    assert switch.available is True
    assert sensor.available is True
    assert cover is not None
    assert cover.available is True
    assert climate is not None
    assert climate.available is True
    assert fan.available is True


def test_legacy_payload_explicit_offline_stays_unavailable() -> None:
    """明确 online=false 仍必须显示不可用，不能被 fallback 默认值覆盖."""
    light = project_light({
        "device_id": "legacy-light-offline",
        "category": "light",
        "online": False,
        "params": {"p": True, "l": 80},
    }, domain=DOMAIN)
    switch = project_switches({
        "device_id": "legacy-switch-offline",
        "category": "relay_switch",
        "online": False,
        "params": {"1-p": True},
    }, domain=DOMAIN)[0]
    event = project_events({
        "device_id": "legacy-panel-offline",
        "category": "scene_panel",
        "online": False,
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "model-panel",
                "manufacturer": "Yeelight",
                "model": "情景面板",
                "category": "scene_panel",
            },
            "components": [
                {
                    "component_id": "scene_button",
                    "category": "scene_panel",
                    "events": [{"event_id": 1, "name": "click"}],
                }
            ],
        },
    }, domain=DOMAIN)[0]

    assert light is not None
    assert light.available is False
    assert switch.available is False
    assert event.available is False
