"""Runtime inference coverage for documented Yeelight IoT component samples."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.capabilities.data import IOT_COMPONENT_SPECS
from custom_components.yeelight_pro.capabilities.models import IoTComponentSpec
from custom_components.yeelight_pro.capabilities.registry import property_spec
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates

PRIMARY_RUNTIME_PLATFORMS = frozenset({
    "binary_sensor",
    "climate",
    "cover",
    "event",
    "fan",
    "light",
    "sensor",
    "switch",
})
SAMPLE_SKIPPED_PROPS = frozenset({
    "3rdPartySyncBitmask",
    "deviceKey",
    "icon",
    "io",
    "ip",
    "ltk",
    "mac",
    "mock",
    "name",
})


def _attach(payload: dict) -> dict:
    """Attach runtime-inferred canonical models for one payload."""
    DevicePayloadBuilder().attach_canonical_models_if_available(payload)
    return payload


def _documented_primary_components() -> list[IoTComponentSpec]:
    """Return documented runtime components with HA primary platform hints."""
    return [
        component
        for component in IOT_COMPONENT_SPECS
        if component.category not in {None, "gateway", "other"}
        and component.platform_hint in PRIMARY_RUNTIME_PLATFORMS
    ]


def _sample_component_props(component: IoTComponentSpec) -> dict[str, object]:
    """Build runtime values from documented component properties."""
    return {
        prop: _sample_property_value(prop)
        for prop in component.properties
        if prop and prop not in SAMPLE_SKIPPED_PROPS
    }


def _sample_property_value(prop: str) -> object:
    """Return a representative runtime value for a documented property."""
    spec = property_spec(prop)
    data_type = (spec.data_type if spec is not None else "").lower()
    if spec is not None and spec.value_list:
        return next(iter(spec.value_list))
    if prop in {
        "acp",
        "alm",
        "bc",
        "bcg",
        "ct_rdy",
        "dc",
        "mv",
        "o",
        "p",
        "rfhp",
        "slisaon_rdy",
        "sp",
        "vmcp",
    }:
        return True
    if prop == "c":
        return 16711680
    if prop == "ct":
        return 4000
    if "bool" in data_type:
        return True
    if "enum" in data_type:
        return "1"
    if any(token in data_type for token in ("double", "float", "int", "number")):
        return 50
    return "sample"


@pytest.mark.parametrize(
    "component",
    _documented_primary_components(),
    ids=lambda item: item.alias,
)
def test_documented_runtime_component_projects_primary_platform(
    component: IoTComponentSpec,
) -> None:
    """官方组件身份和属性应生成对应 HA 主平台，而不是只剩控制项。"""
    payload = _attach({
        "device_id": f"runtime-component-{component.component_id}",
        "category": component.category,
        "type": component.category,
        "component_id": component.alias,
        "params": _sample_component_props(component),
        "online": True,
    })

    candidates = {
        (item.platform, item.component_id, item.entity_category)
        for item in iter_device_entity_candidates(payload)
    }

    assert len(_documented_primary_components()) >= 28
    assert (component.platform_hint or "", component.category or "") != ("", "")
    assert component.platform_hint in {item[0] for item in candidates}


def test_documented_runtime_component_matrix_keeps_high_value_samples() -> None:
    """矩阵必须持续覆盖真实资料中的高价值组件样本。"""
    aliases = {component.alias for component in _documented_primary_components()}

    assert {
        "dali illuminance sensor",
        "floor heating",
        "switch light",
        "temp control",
        "wireless switch channel",
        "zebra blinds",
        "zonalShieldIlluminanceRadarSensor",
    } <= aliases


def test_runtime_component_identity_keeps_switch_light_as_light() -> None:
    """官方开关灯组件只有 p 时，也应按组件身份生成 light 主实体。"""
    payload = _attach({
        "device_id": "runtime-switch-light",
        "category": "light",
        "type": "light",
        "component_id": "switch light",
        "params": {
            "p": True,
            "slisaon": 1,
            "bp": "1",
            "dd": 1000,
            "slisaon_rdy": True,
        },
        "online": True,
    })

    candidates = {
        (item.platform, item.component_id, item.entity_category)
        for item in iter_device_entity_candidates(payload)
    }
    product_component = payload["ha_product_model"]["components"][0]

    assert product_component["cid"] == 2
    assert product_component["name"] == "开关灯"
    assert product_component["category"] == "light"
    assert ("light", "light", None) in candidates
    assert ("select", "light_bp_select", "config") in candidates
    assert ("number", "light_dd_number", "config") in candidates
    assert ("select", "light_slisaon_select", "config") in candidates
    assert ("binary_sensor", "slisaon_ready", "diagnostic") in candidates


def test_runtime_floor_heating_projects_climate_from_iot_props() -> None:
    """地暖官方 rfh* 属性应生成 climate，而不是只剩诊断 sensor。"""
    payload = _attach({
        "device_id": "runtime-floor-heating",
        "category": "temp_control",
        "type": "temp_control",
        "component_id": "floor heating",
        "params": {"rfhp": True, "rfhct": 23, "rfhtt": 25},
        "online": True,
    })

    candidates = {
        (item.platform, item.component_id, item.entity_category)
        for item in iter_device_entity_candidates(payload)
    }
    product_component = payload["ha_product_model"]["components"][0]

    assert product_component["cid"] == 43
    assert product_component["name"] == "地暖"
    assert product_component["category"] == "temp_control"
    assert ("climate", "temp_control", None) in candidates
    assert ("sensor", "floor_heating_temperature", None) not in candidates


def test_runtime_temp_control_projects_climate_and_config_controls() -> None:
    """温控器组件 p/t/tgt 与扩展属性应生成 climate 和配置控件。"""
    payload = _attach({
        "device_id": "runtime-temp-control",
        "category": "temp_control",
        "type": "temp_control",
        "component_id": "temp control",
        "params": {
            "p": True,
            "t": 24,
            "tgt": 26,
            "bhm": "2",
            "do": 15,
            "ve": "3",
            "fa": "1",
            "he": "0",
            "sa": 90,
        },
        "online": True,
    })

    candidates = {
        (item.platform, item.component_id, item.entity_category)
        for item in iter_device_entity_candidates(payload)
    }

    assert ("climate", "temp_control", None) in candidates
    assert ("select", "temp_control_bhm_select", None) in candidates
    assert ("number", "temp_control_do_number", None) in candidates
    assert ("select", "temp_control_ve_select", None) in candidates
    assert ("select", "temp_control_fa_select", None) in candidates
    assert ("select", "temp_control_he_select", None) in candidates
    assert ("number", "temp_control_sa_number", "config") in candidates
