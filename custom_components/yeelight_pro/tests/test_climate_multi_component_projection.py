"""Multi-component climate projection regressions."""

from __future__ import annotations

import pytest

from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from custom_components.yeelight_pro.climate import YeelightProClimate
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.projector.climate import project_climate, project_climates
from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
)
from custom_components.yeelight_pro.projector.sensor import project_sensors

from .projection_helpers import DOMAIN, projection_payload


def multi_climate_payload() -> dict:
    """Build a schema-aware payload with two independent climate components."""
    payload = projection_payload(
        device_id="climate-dual-1",
        category="temp_control",
        component_id="air_conditioner_1",
        state={"acp": True, "acm": 1, "acf": 4, "acct": 24, "actt": 26},
        component_category="air_conditioner",
    )
    payload["params"] = {
        "1-acp": True,
        "1-acm": 1,
        "1-acf": 4,
        "1-acct": 24,
        "1-actt": 26,
        "2-acp": False,
        "2-acm": 8,
        "2-acf": 2,
        "2-acct": 22,
        "2-actt": 20,
    }
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "air_conditioner_1": {
                "acp": "1-acp",
                "acm": "1-acm",
                "acf": "1-acf",
                "acct": "1-acct",
                "actt": "1-actt",
            },
            "air_conditioner_2": {
                "acp": "2-acp",
                "acm": "2-acm",
                "acf": "2-acf",
                "acct": "2-acct",
                "actt": "2-actt",
            },
        }
    }
    payload["ha_device_instance"]["components"] = [
        _climate_instance_component("air_conditioner_1", True, 1, 4, 24, 26),
        _climate_instance_component("air_conditioner_2", False, 8, 2, 22, 20),
    ]
    payload["ha_product_model"]["components"] = [
        _climate_schema_component("air_conditioner_1"),
        _climate_schema_component("air_conditioner_2"),
    ]
    return payload


def test_multi_climate_components_project_multiple_climates() -> None:
    """多温控组件应拆成多个 climate，而不是只保留第一个."""
    projections = project_climates(multi_climate_payload(), domain=DOMAIN)

    assert [item.name for item in projections] == ["空调控制器", "空调控制器"]
    assert [(item.component_id, item.current_temperature) for item in projections] == [
        ("air_conditioner_1", 24),
        ("air_conditioner_2", 22),
    ]
    assert [item.target_temperature for item in projections] == [26, 20]
    assert [item.hvac_mode for item in projections] == [HVACMode.COOL, HVACMode.OFF]
    assert [item.fan_mode for item in projections] == ["低", "中"]
    assert all(
        item.supported_features
        & (ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE)
        for item in projections
    )
    assert [item.unique_id for item in projections] == [
        "yeelight_pro_climate-dual-1_air_conditioner_1_climate",
        "yeelight_pro_climate-dual-1_air_conditioner_2_climate",
    ]
    assert [item.power_key for item in projections] == ["1-acp", "2-acp"]
    assert [item.target_temperature_key for item in projections] == ["1-actt", "2-actt"]
    assert [item.mode_key for item in projections] == ["1-acm", "2-acm"]
    assert [item.fan_mode_key for item in projections] == ["1-acf", "2-acf"]
    first_climate = project_climate(multi_climate_payload(), domain=DOMAIN)
    assert first_climate is not None
    assert first_climate.component_id == "air_conditioner_1"


def test_multi_climate_components_create_climate_candidates() -> None:
    """候选层必须保留每个温控组件，供 registry cleanup 正确对账."""
    candidates = [
        item
        for item in iter_device_entity_candidates(multi_climate_payload())
        if item.platform == "climate"
    ]

    assert [(item.component_id, item.unique_id) for item in candidates] == [
        ("air_conditioner_1", "yeelight_pro_climate-dual-1_air_conditioner_1_climate"),
        ("air_conditioner_2", "yeelight_pro_climate-dual-1_air_conditioner_2_climate"),
    ]
    assert [item.source for item in candidates] == ["device", "device"]
    assert all(item.device_id == "climate-dual-1" for item in candidates)


def test_multi_climate_main_properties_do_not_duplicate_helper_entities() -> None:
    """acm/acf/acdfltr 已由 climate 表达时不应重复成为 number/sensor."""
    payload = multi_climate_payload()
    for component in payload["ha_product_model"]["components"]:
        component["properties"].append({"prop_id": "acdfltr", "access": "read_write"})
    for component in payload["ha_device_instance"]["components"]:
        component["state"]["acdfltr"] = 80

    numbers = project_number_controls(payload, domain=DOMAIN)
    sensors = project_sensors(payload, domain=DOMAIN)

    assert [
        (item.component_id, item.prop_id)
        for item in numbers
        if item.prop_id in {"acm", "acf", "acdfltr"}
    ] == []
    assert [
        (item.component_id, item.name)
        for item in sensors
        if item.component_id.endswith(("ac_mode", "ac_fan", "ac_deflector"))
    ] == []


@pytest.mark.asyncio
async def test_multi_climate_entity_uses_component_control_key(mock_coordinator) -> None:
    """组件级 climate 控制应写入 N-actt/N-acp，而不是压回顶层 actt/acp."""
    mock_coordinator.get_device.return_value = multi_climate_payload()
    climate = YeelightProClimate(
        mock_coordinator,
        "climate-dual-1",
        component_id="air_conditioner_2",
    )

    await climate.async_set_temperature(temperature=23)
    await climate.async_set_hvac_mode(HVACMode.HEAT)
    await climate.async_set_fan_mode("中")

    assert mock_coordinator.async_control_device.await_args_list[0].args == (
        "climate-dual-1",
        {"2-actt": 23.0},
    )
    assert mock_coordinator.async_control_device.await_args_list[1].args == (
        "climate-dual-1",
        {"2-acp": True, "2-acm": 8},
    )
    assert mock_coordinator.async_control_device.await_args_list[2].args == (
        "climate-dual-1",
        {"2-acf": 2},
    )


def _climate_instance_component(
    component_id: str,
    power: bool,
    mode: int,
    fan_speed: int,
    current_temperature: int,
    target_temperature: int,
) -> dict:
    """Return runtime state for one climate component."""
    return {
        "component_id": component_id,
        "category": "air_conditioner",
        "available": True,
        "state": {
            "acp": power,
            "acm": mode,
            "acf": fan_speed,
            "acct": current_temperature,
            "actt": target_temperature,
        },
    }


def _climate_schema_component(component_id: str) -> dict:
    """Return product-schema evidence for one climate component."""
    return {
        "component_id": component_id,
        "category": "air_conditioner",
        "name": "air_conditioner",
        "component_type": "air_conditioner",
        "properties": [
            {"prop_id": "acp", "access": "read_write"},
            {"prop_id": "acm", "access": "read_write"},
            {"prop_id": "acf", "access": "read_write"},
            {"prop_id": "acct", "access": "read"},
            {"prop_id": "actt", "access": "read_write"},
        ],
        "events": [],
    }


__all__ = ["multi_climate_payload"]
