"""Entity candidate regressions for Yeelight IoT model boundaries."""

from __future__ import annotations

from typing import Any

from custom_components.yeelight_pro.entity_candidates import (
    iter_device_entity_candidates,
)


def test_fresh_air_temp_control_category_projects_only_fan_candidate() -> None:
    """新风属于 temp_control 大类，具体 fan 能力由 vmcp/vmcf 决定。"""
    candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(_fresh_air_payload())
    }

    assert candidates == {("fan", "fresh_air")}
    assert ("climate", "climate") not in candidates


def test_user_named_smoke_contact_sensor_projects_from_capabilities() -> None:
    """用户命名不能覆盖易来物模型能力；dc/alm 应投影为门磁二元实体。"""
    candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(
            {
                "device_id": "contact-1",
                "name": "厨房烟雾传感器",
                "category": "light",
                "type": "light",
                "params": {"dc": False, "alm": True, "bl": 88},
                "online": True,
            }
        )
    }

    assert {
        ("binary_sensor", "door"),
        ("binary_sensor", "tamper"),
        ("sensor", "battery"),
    } <= candidates
    assert not any(platform in {"light", "switch", "event"} for platform, _ in candidates)


def test_name_only_smoke_light_does_not_project_entities() -> None:
    """没有属性、事件或 schema 证据时，用户名称不能生成任何 HA 实体。"""
    candidates = list(
        iter_device_entity_candidates(
            {
                "device_id": "name-only-smoke-1",
                "name": "厨房烟雾传感器",
                "category": "light",
                "type": "light",
                "params": {},
                "online": True,
            }
        )
    )

    assert candidates == []


def _fresh_air_payload() -> dict[str, Any]:
    return {
        "device_id": "fresh-air-1",
        "category": "temp_control",
        "params": {"1-vmcp": True, "1-vmcf": 30},
        "ha_device_instance": {
            "device_id": "fresh-air-1",
            "name": "新风",
            "online": True,
            "device_info": {
                "identifiers": [["yeelight_pro", "fresh-air-1"]],
                "manufacturer": "Yeelight",
                "model": "新风",
                "name": "新风",
            },
            "extensions": {
                "component_state_keys": {
                    "fresh_air": {"vmcp": "1-vmcp", "vmcf": "1-vmcf"}
                }
            },
            "components": [
                {
                    "component_id": "fresh_air",
                    "name": "新风",
                    "category": "temp_control",
                    "available": True,
                    "state": {"vmcp": True, "vmcf": 30},
                }
            ],
        },
        "ha_product_model": {
            "schema_version": "runtime-v1",
            "product": {
                "model_id": "runtime-fresh-air",
                "manufacturer": "Yeelight",
                "model": "新风",
                "category": "temp_control",
            },
            "components": [
                {
                    "component_id": "fresh_air",
                    "name": "新风",
                    "category": "temp_control",
                    "properties": [
                        {"prop_id": "vmcp", "access": "read_write", "format": "boolean"},
                        {
                            "prop_id": "vmcf",
                            "access": "read_write",
                            "format": "uint8",
                            "value_range": {"min": 1, "max": 100, "step": 1},
                        },
                    ],
                    "events": [],
                }
            ],
        },
    }
