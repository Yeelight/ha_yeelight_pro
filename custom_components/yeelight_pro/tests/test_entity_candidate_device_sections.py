"""Device-page section coverage for Yeelight Pro entity candidates."""

from __future__ import annotations

from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates

from .test_entity_candidates import _light_payload


def test_schema_rich_device_projects_device_page_sections() -> None:
    """schema 丰富设备必须同时提供控制、传感器、事件、配置和诊断候选."""
    payload = _light_payload()
    payload["device_id"] = "rich-light-1"
    payload["ha_device_instance"]["device_id"] = "rich-light-1"
    payload["ha_device_instance"]["device_info"]["identifiers"] = [
        ["yeelight_pro", "rich-light-1"]
    ]
    payload["ha_device_instance"]["components"][0]["state"] = {
        "p": True,
        "l": 70,
        "t": 31,
        "bl": 86,
        "li": 1,
        "rd": "0",
        "min_level": 10,
    }
    payload["ha_product_model"]["components"][0] = {
        "component_id": "main_light",
        "category": "color temperature light",
        "properties": [
            {"prop_id": "p", "access": "read_write", "property_type": "bool"},
            {"prop_id": "l", "access": "read_write", "value_range": {"min": 1, "max": 100}},
            {"prop_id": "t", "access": "read", "property_type": "int"},
            {"prop_id": "bl", "access": "read", "property_type": "int"},
            {"prop_id": "li", "access": "read_write", "property_type": "int"},
            {"prop_id": "rd", "access": "read_write", "property_type": "int"},
            {
                "prop_id": "min_level",
                "access": "read_write",
                "property_type": "int",
                "value_range": {"min": 0, "max": 100, "step": 1},
            },
        ],
        "events": [
            {"event_id": "click", "name": "点击"},
            {"event_id": "hold", "name": "长按"},
        ],
    }

    candidates = {
        (item.platform, item.component_id): item
        for item in iter_device_entity_candidates(payload)
    }

    assert candidates[("light", "main_light")].entity_category is None
    assert candidates[("sensor", "temperature")].entity_category is None
    assert candidates[("sensor", "battery")].entity_category == "diagnostic"
    assert candidates[("switch", "main_light_li_switch")].entity_category == "config"
    assert candidates[("select", "main_light_rd_select")].entity_category == "config"
    assert candidates[("number", "main_light_min_level_number")].entity_category == "config"
    assert candidates[("event", "main_light")].entity_category is None
    assert candidates[("event", "main_light")].name is None
