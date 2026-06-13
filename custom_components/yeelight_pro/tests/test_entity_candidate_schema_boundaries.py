"""Entity candidate schema-boundary tests for Yeelight Pro."""

from __future__ import annotations

from custom_components.yeelight_pro.entity_candidates import (
    collect_entity_candidate_keys,
    iter_device_entity_candidates,
)

from .entity_candidate_test_helpers import _Coordinator, _light_payload


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
