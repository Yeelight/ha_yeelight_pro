"""Entity candidate tests for Yeelight Pro."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from custom_components.yeelight_pro.entity_candidates import (
    collect_entity_candidate_keys,
    iter_device_entity_candidates,
    iter_entity_candidates,
)
from custom_components.yeelight_pro.entity_lifecycle import collect_active_entity_keys


@dataclass
class _Coordinator:
    """Minimal coordinator shape required by entity candidate projection."""

    data: Mapping[Any, Mapping[str, Any]]
    scenes: list[dict[str, Any]] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    house_id: int | None = None
    hide_unknown_entities: bool = True
    options: dict[str, Any] = field(default_factory=dict)


def _light_payload() -> dict[str, Any]:
    """Build a minimal canonical light payload."""
    return {
        "device_id": "light-1",
        "category": "light",
        "type": "light",
        "online": True,
        "params": {"p": True, "l": 80},
        "ha_device_instance": {
            "device_id": "light-1",
            "name": "Light",
            "online": True,
            "device_info": {
                "identifiers": [["yeelight_pro", "light-1"]],
                "manufacturer": "Yeelight",
                "model": "light",
                "name": "Light",
            },
            "components": [
                {
                    "component_id": "main_light",
                    "category": "color temperature light",
                    "available": True,
                    "state": {"p": True, "l": 80},
                }
            ],
        },
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "model-light-1",
                "manufacturer": "Yeelight",
                "model": "light",
                "category": "light",
            },
            "components": [
                {
                    "component_id": "main_light",
                    "category": "color temperature light",
                    "events": [],
                }
            ],
        },
    }


def test_entity_candidates_match_lifecycle_active_keys() -> None:
    """候选 key 必须与 lifecycle 当前 active key 完全等价."""
    coordinator = _Coordinator(
        data={
            "light-1": _light_payload(),
            "relay-1": {
                "device_id": "relay-1",
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {"1-p": True, "2-sp": False},
            },
            "vacuum-1": {
                "device_id": "vacuum-1",
                "category": "other",
                "type": "vacuum",
                "online": True,
                "params": {"status": "cleaning", "battery": 80},
            },
        },
        scenes=[{"id": "scene_1"}],
        groups=[{"id": "group_1"}],
        house_id=12345,
    )

    candidate_keys = collect_entity_candidate_keys(coordinator)

    assert candidate_keys == collect_active_entity_keys(coordinator)
    assert ("light", "yeelight_pro_light-1_main_light") in candidate_keys
    assert ("switch", "yeelight_pro_relay-1_switch_1") in candidate_keys
    assert ("switch", "yeelight_pro_relay-1_switch_2") in candidate_keys
    assert all(platform != "vacuum" for platform, _unique_id in candidate_keys)
    assert ("button", "yeelight_pro_scene_scene_1") in candidate_keys
    assert ("scene", "yeelight_pro_scene_scene_1") not in candidate_keys


def test_entity_candidates_apply_device_import_filter_to_device_sources_only() -> None:
    """真实设备 picker/filter 只影响设备来源候选，保留拓扑辅助候选."""
    blocked_payload = _light_payload()
    blocked_payload["device_id"] = "blocked-light"
    blocked_payload["ha_device_instance"]["device_id"] = "blocked-light"
    blocked_payload["ha_device_instance"]["device_info"]["identifiers"] = [
        ["yeelight_pro", "blocked-light"]
    ]
    coordinator = _Coordinator(
        data={
            "light-1": _light_payload(),
            "blocked-light": blocked_payload,
        },
        scenes=[{"id": "scene_1"}],
        options={
            "device_import_filter": {
                "enabled": True,
                "exclude": {"devices": ["blocked-light"]},
            }
        },
    )

    candidate_keys = collect_entity_candidate_keys(coordinator)

    assert ("light", "yeelight_pro_light-1_main_light") in candidate_keys
    assert ("light", "yeelight_pro_blocked-light_main_light") not in candidate_keys
    assert ("button", "yeelight_pro_scene_scene_1") in candidate_keys


def test_device_entity_candidate_metadata_is_diagnostics_safe() -> None:
    """候选元数据只保留平台、来源、设备和组件索引，不携带 raw payload."""
    candidates = list(iter_device_entity_candidates(_light_payload()))

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.platform == "light"
    assert candidate.unique_id == "yeelight_pro_light-1_main_light"
    assert candidate.source == "device"
    assert candidate.device_id == "light-1"
    assert candidate.component_id == "main_light"
    assert candidate.available is True
    assert candidate.availability_reason is None


def test_device_entity_candidate_tracks_unavailable_projection() -> None:
    """候选层应保留可用性聚合所需的 unavailable 状态."""
    payload = _light_payload()
    payload["online"] = False
    payload["ha_device_instance"]["online"] = False

    candidates = list(iter_device_entity_candidates(payload))

    assert len(candidates) == 1
    assert candidates[0].available is False
    assert candidates[0].availability_reason == "unavailable"


def test_gateway_and_unknown_indexed_power_do_not_create_candidates() -> None:
    """网关仅生成诊断候选，未知 indexed p/sp 仍不生成普通实体候选."""
    coordinator = _Coordinator(
        data={
            "gateway": {
                "device_id": "gateway-1",
                "category": "gateway",
                "type": "gateway",
                "online": True,
                "params": {"fm": 1024, "lf": 60, "lc": 1},
            },
            "unknown": {
                "device_id": "unknown-1",
                "category": "other",
                "type": "sensor",
                "online": True,
                "params": {"1-p": True, "2-sp": False},
                "hide_unknown_entities": False,
            },
        },
        hide_unknown_entities=False,
    )

    candidates = list(iter_entity_candidates(coordinator))

    assert {
        (item.platform, item.component_id, item.name)
        for item in candidates
    } == {
        ("sensor", "free_memory", "剩余内存"),
        ("sensor", "lan_control", "局域网控制配置"),
        ("sensor", "uptime", "运行时间"),
    }
    assert not any(item.platform in {"light", "switch"} for item in candidates)


def test_empty_schema_state_keeps_available_unknown_sensor_candidates() -> None:
    """只有 schema、没有当前值时仍生成 available 实体，状态由 HA 显示 unknown。"""
    coordinator = _Coordinator(
        data={
            "temp": {
                "device_id": "temp-empty",
                "category": "other",
                "online": True,
                "ha_device_instance": {
                    "device_id": "temp-empty",
                    "name": "温湿度传感器",
                    "online": True,
                    "device_info": {
                        "identifiers": [["yeelight_pro", "device:temp-empty"]],
                        "manufacturer": "Yeelight",
                        "model": "温湿度传感器",
                        "name": "温湿度传感器",
                    },
                    "components": [
                        {
                            "component_id": "temp_humidity",
                            "category": "temperature humidity sensor",
                            "available": True,
                            "state": {},
                        }
                    ],
                },
                "ha_product_model": {
                    "schema_version": "v1",
                    "product": {
                        "model_id": "model-temp",
                        "manufacturer": "Yeelight",
                        "model": "温湿度传感器",
                        "category": "other",
                    },
                    "components": [
                        {
                            "component_id": "temp_humidity",
                            "category": "temperature humidity sensor",
                            "properties": [
                                {"prop_id": "t", "access": "read"},
                                {"prop_id": "h", "access": "read"},
                            ],
                            "events": [],
                        }
                    ],
                },
            }
        },
    )

    candidates = list(iter_entity_candidates(coordinator))

    assert {
        (item.platform, item.component_id, item.available)
        for item in candidates
    } == {
        ("sensor", "temperature", True),
        ("sensor", "humidity", True),
    }


def test_entity_candidates_include_registry_metadata_for_major_platforms() -> None:
    """生命周期同步需要候选层提供主要平台的中文名称和图标。"""
    coordinator = _Coordinator(
        data={
            "light": _light_payload(),
            "cover": {
                "device_id": "cover-1",
                "category": "curtain",
                "online": True,
                "params": {"cp": 20, "tp": 80},
            },
            "climate": {
                "device_id": "climate-1",
                "category": "temp_control",
                "online": True,
                "params": {"aco": True, "acct": 24, "actt": 26},
            },
        },
        scenes=[{"id": "scene_1", "name": "回家"}],
        groups=[{"id": "group_1", "name": "客厅灯组"}],
        house_id=12345,
    )

    candidates = {
        (item.platform, item.unique_id): item
        for item in iter_entity_candidates(coordinator)
    }

    assert candidates[("light", "yeelight_pro_light-1_main_light")].name is None
    assert candidates[("light", "yeelight_pro_light-1_main_light")].icon == "mdi:lightbulb"
    assert candidates[("cover", "yeelight_pro_cover-1_cover")].name == "窗帘"
    assert candidates[("climate", "yeelight_pro_climate-1_climate")].name == "温控"
    assert candidates[("button", "yeelight_pro_scene_scene_1")].name == "回家"
    assert candidates[("number", "yeelight_pro_group_group_1_brightness")].name == "客厅灯组 亮度"
    assert candidates[("select", "yeelight_pro_12345_select_room")].name == "当前房间"


def test_schema_unknown_actions_do_not_create_device_buttons() -> None:
    """未知产品动作不能在缺少官方执行 API 时泛化成设备 button。"""
    payload = _light_payload()
    payload["device_id"] = "action-device-1"
    payload["ha_device_instance"]["device_id"] = "action-device-1"
    payload["ha_device_instance"]["device_info"]["identifiers"] = [
        ["yeelight_pro", "action-device-1"]
    ]
    payload["ha_product_model"]["components"][0]["actions"] = [
        {
            "action_id": "vendor_reset",
            "name": "vendor reset",
            "in": [],
            "out": [],
        }
    ]

    candidate_keys = collect_entity_candidate_keys(_Coordinator(data={"device": payload}))

    assert ("light", "yeelight_pro_action-device-1_main_light") in candidate_keys
    assert not any(key[0] == "button" for key in candidate_keys)


def test_schema_writable_auxiliary_properties_create_control_candidates() -> None:
    """可写辅助属性应按类型进入 switch/select 生命周期候选集合."""
    payload = _light_payload()
    payload["device_id"] = "aux-device-1"
    payload["ha_device_instance"]["device_id"] = "aux-device-1"
    payload["ha_device_instance"]["components"][0]["state"].update({
        "acrc": True,
        "li": 1,
        "rd": "0",
    })
    payload["ha_device_instance"]["device_info"]["identifiers"] = [
        ["yeelight_pro", "aux-device-1"]
    ]
    payload["ha_product_model"]["components"][0]["properties"] = [
        {"prop_id": "l", "access": "read_write", "value_range": {"min": 1, "max": 100}},
        {
            "prop_id": "acrc",
            "name": "空调遥控器",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        },
        {
            "prop_id": "li",
            "name": "指示灯",
            "access": "read_write",
            "property_type": "int",
        },
        {
            "prop_id": "rd",
            "name": "电机方向",
            "access": "read_write",
            "property_type": "int",
        },
    ]

    candidates = {
        (item.platform, item.unique_id): item
        for item in iter_device_entity_candidates(payload)
    }

    assert ("switch", "yeelight_pro_aux-device-1_main_light_acrc_switch") in candidates
    assert ("switch", "yeelight_pro_aux-device-1_main_light_li_switch") in candidates
    assert ("select", "yeelight_pro_aux-device-1_main_light_rd_select") in candidates
    assert not any(unique_id.endswith("_l_number") for _platform, unique_id in candidates)
