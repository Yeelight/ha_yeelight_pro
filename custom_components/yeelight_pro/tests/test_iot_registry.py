"""Yeelight IoT 物模型能力注册表回归测试."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.capabilities import (
    iot_registry,
    is_iot_category,
)
from custom_components.yeelight_pro.capabilities.mapping import (
    component_platform_hint,
    platform_for_category,
)
from custom_components.yeelight_pro.capabilities.properties import property_capability


CORE_IOT_CATEGORIES = {
    "light": "light",
    "contact_sensor": "binary_sensor",
    "human_sensor": "binary_sensor",
    "light_sensor": "sensor",
    "curtain": "cover",
    "temp_control": "climate",
    "relay_switch": "switch",
    "scene_panel": "event",
    "gateway": None,
    "knob_switch": "event",
    "other": "sensor",
}

HA_ENTITY_PLATFORMS_NOT_IOT_CATEGORIES = {
    "event",
    "scene",
    "button",
    "select",
    "number",
    "text",
}


def test_registry_loads_core_iot_data() -> None:
    """registry 必须集中加载首版 Yeelight IoT 核心事实."""
    registry = iot_registry()

    assert len(registry.categories) == 11
    assert len(registry.components) >= 10
    assert len(registry.properties) >= 16
    assert len(registry.events) >= 10
    assert len(registry.protocols) == 6


def test_core_iot_categories_map_to_ha_platforms() -> None:
    """核心 IoT 品类应映射到首版 HA 平台或显式拓扑设备."""
    for category, platform in CORE_IOT_CATEGORIES.items():
        assert is_iot_category(category)
        assert platform_for_category(category) == platform


def test_ha_entity_platforms_are_not_iot_categories() -> None:
    """HA 平台表达不能被当成 Yeelight IoT 设备品类."""
    for platform in HA_ENTITY_PLATFORMS_NOT_IOT_CATEGORIES:
        assert not is_iot_category(platform)
        assert platform_for_category(platform) is None


@pytest.mark.parametrize(
    ("component", "expected"),
    [
        ("color temperature light", "light"),
        ("color light without temperature", "light"),
        (72, "light"),
        ("contact sensor", "binary_sensor"),
        ("human detection sensor", "binary_sensor"),
        ("ambient light sensor", "sensor"),
        ("curtain", "cover"),
        ("air conditioner", "climate"),
        ("floor heating", "climate"),
        ("fresh air", "fan"),
        ("switch control", "switch"),
        ("switch_control", "switch"),
        ("wireless switch channel", "switch"),
        ("scene control button", "button"),
        ("dali scene control button", "button"),
        ("gateway", "sensor"),
        (1, "sensor"),
        ("dali energy", "sensor"),
        (66, "sensor"),
        ("power meter", "sensor"),
        (76, "sensor"),
        ("knob switch", "event"),
    ],
)
def test_core_component_platform_hints(component: str, expected: str) -> None:
    """核心组件 hint 应表达现有投影入口需要的平台语义."""
    assert component_platform_hint(component) == expected


@pytest.mark.parametrize(
    ("prop", "device_class", "unit", "control_key"),
    [
        ("p", None, None, "power"),
        ("l", None, "%", "brightness"),
        ("ct", None, "K", "color_temperature"),
        ("c", None, "rgb", "rgb_color"),
        ("t", "temperature", "°C", None),
        ("h", "humidity", "%", None),
        ("luminance", "illuminance", "lx", None),
        ("mv", "motion", None, None),
        ("dc", "door", None, None),
        ("alm", "tamper", None, None),
        ("tp", None, "%", "target_position"),
        ("cp", None, "%", "current_position"),
        ("sp", None, None, "switch_power"),
        ("curp", "power", "W", None),
        ("iec", "energy", "Wh", None),
        ("ap", "power", "W", None),
        ("ae", "energy", "Wh", None),
        ("bl", "battery", "%", None),
    ],
)
def test_core_property_capabilities(
    prop: str,
    device_class: str | None,
    unit: str | None,
    control_key: str | None,
) -> None:
    """高频属性必须暴露 HA 语义能力."""
    capability = property_capability(prop)

    assert capability is not None
    assert capability.device_class == device_class
    assert capability.unit == unit
    assert capability.control_key == control_key


def test_property_specs_keep_hashable_dataclass_contract() -> None:
    """冻结模型可作为集合成员，枚举映射不应破坏 dataclass hash."""
    spec = iot_registry().property_spec("l")

    assert spec is not None
    assert isinstance(hash(spec), int)


def test_power_meter_specs_match_iot_csv_access_boundary() -> None:
    """电量组件属性来自本地 CSV：curp/iec 均为应用类只读设备属性."""
    registry = iot_registry()

    curp = registry.property_spec("curp")
    iec = registry.property_spec("iec")

    assert curp is not None
    assert curp.full_name == "current power"
    assert curp.category == "application"
    assert curp.handler == "device"
    assert curp.readable is True
    assert curp.writable is False
    assert iec is not None
    assert iec.readable is True
    assert iec.writable is False


def test_dali_energy_specs_match_iot_csv_boundary() -> None:
    """dali能量组件来自本地 CSV：首版只消费明确的 ap/ae 遥测。"""
    registry = iot_registry()

    component = registry.component_map["dali energy"]
    assert component.component_id == 66
    assert component.category is None
    assert component.component_type == "global"
    assert component.platform_hint == "sensor"
    assert component.properties == (
        "ap",
        "ae",
        "ot",
        "sys_s",
        "esv",
        "esvf",
        "temp",
        "ocp",
        "lsot",
        "lsv",
        "lsc",
        "pf",
    )

    active_power = registry.property_spec("ap")
    active_energy = registry.property_spec("ae")

    assert active_power is not None
    assert active_power.full_name == "active power"
    assert active_power.readable is True
    assert active_power.writable is False
    assert active_power.components == ("dali energy",)
    assert active_energy is not None
    assert active_energy.full_name == "active energy"
    assert active_energy.readable is True
    assert active_energy.writable is False
    assert active_energy.components == ("dali energy",)

    for prop_name in ("ot", "sys_s", "esv", "esvf", "ocp", "lsot", "lsv", "lsc", "pf"):
        prop = registry.property_spec(prop_name)
        assert prop is not None
        assert prop.readable is True
        assert "dali energy" in prop.components
        assert registry.property_capability(prop_name) is None

    temperature = registry.property_spec("temp")
    assert temperature is not None
    assert temperature.readable is True


def test_color_light_without_temperature_matches_iot_csv_boundary() -> None:
    """无色温彩光灯来自本地 CSV：只有开关、亮度和 RGB，不应关联 ct。"""
    registry = iot_registry()

    component = registry.component_map["color light without temperature"]
    assert component.component_id == 72
    assert component.category == "light"
    assert component.platform_hint == "light"
    assert component.properties == ("p", "l", "c")

    for prop_name in ("p", "l", "c"):
        prop = registry.property_spec(prop_name)
        assert prop is not None
        assert "color light without temperature" in prop.components

    color_temp = registry.property_spec("ct")
    assert color_temp is not None
    assert "color light without temperature" not in color_temp.components
