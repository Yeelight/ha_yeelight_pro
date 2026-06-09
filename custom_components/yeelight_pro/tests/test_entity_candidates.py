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
    automations: list[dict[str, Any]] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    house_id: int | None = None
    hide_unknown_entities: bool = True
    analytics_runtime_enabled: bool = False


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
        automations=[{"id": "auto_1"}],
        groups=[{"id": "group_1"}],
        house_id=12345,
    )

    candidate_keys = collect_entity_candidate_keys(coordinator)

    assert candidate_keys == collect_active_entity_keys(coordinator)
    assert ("light", "yeelight_pro_light-1_main_light") in candidate_keys
    assert ("switch", "yeelight_pro_relay-1_switch_1") in candidate_keys
    assert ("switch", "yeelight_pro_relay-1_switch_2") in candidate_keys
    assert ("vacuum", "yeelight_pro_vacuum-1_vacuum") in candidate_keys
    assert ("button", "yeelight_pro_scene_scene_1") in candidate_keys
    assert ("scene", "yeelight_pro_scene_scene_1") in candidate_keys


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


def test_entity_candidates_keep_scene_button_domain_separation() -> None:
    """scene 和 button 可以共用 unique_id，但 candidate key 必须按 HA domain 区分."""
    coordinator = _Coordinator(
        data={},
        scenes=[{"id": "same_scene"}],
    )
    candidates = list(iter_entity_candidates(coordinator))

    assert [(item.platform, item.unique_id) for item in candidates] == [
        ("button", "yeelight_pro_scene_same_scene"),
        ("scene", "yeelight_pro_scene_same_scene"),
    ]
    assert {item.key for item in candidates} == {
        ("button", "yeelight_pro_scene_same_scene"),
        ("scene", "yeelight_pro_scene_same_scene"),
    }


def test_gateway_and_unknown_indexed_power_do_not_create_candidates() -> None:
    """网关和未知 indexed p/sp 仍不生成普通实体候选."""
    coordinator = _Coordinator(
        data={
            "gateway": {
                "device_id": "gateway-1",
                "category": "gateway",
                "type": "gateway",
                "online": True,
                "params": {},
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

    assert list(iter_entity_candidates(coordinator)) == []


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


def test_entity_candidates_include_analytics_sensors_when_enabled() -> None:
    """启用 analytics runtime 后应把 5 个 house-level sensor 计入生命周期候选."""
    candidates = list(
        iter_entity_candidates(
            _Coordinator(
                data={},
                house_id=12345,
                analytics_runtime_enabled=True,
            )
        )
    )

    analytics_candidates = [item for item in candidates if item.source == "analytics"]

    assert [(item.platform, item.unique_id) for item in analytics_candidates] == [
        ("sensor", "yeelight_pro_12345_analytics_alarm_total"),
        ("sensor", "yeelight_pro_12345_analytics_alarm_device_count"),
        ("sensor", "yeelight_pro_12345_analytics_energy_used_kwh"),
        ("sensor", "yeelight_pro_12345_analytics_energy_saved_kwh"),
        ("sensor", "yeelight_pro_12345_analytics_action_total"),
    ]
    assert {item.component_id for item in analytics_candidates} == {
        "alarm_total",
        "alarm_device_count",
        "energy_used_kwh",
        "energy_saved_kwh",
        "action_total",
    }
