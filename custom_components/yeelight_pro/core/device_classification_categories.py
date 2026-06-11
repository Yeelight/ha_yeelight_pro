"""Category normalization data for Yeelight runtime device classification."""

from __future__ import annotations

BROAD_CATEGORIES = frozenset({
    "",
    "binary_sensor",
    "light",
    "relay_switch",
    "sensor",
    "switch",
    "other",
})
GENERIC_PLATFORM_CATEGORIES = frozenset({
    "binary_sensor",
    "sensor",
})

CATEGORY_ALIASES = {
    "binary_sensor": "binary_sensor",
    "binary sensor": "binary_sensor",
    "contact_sensor": "contact_sensor",
    "contact sensor": "contact_sensor",
    "cover": "curtain",
    "curtain": "curtain",
    "gateway": "gateway",
    "human_sensor": "human_sensor",
    "human sensor": "human_sensor",
    "knob_switch": "knob_switch",
    "knob switch": "knob_switch",
    "light": "light",
    "light_sensor": "light_sensor",
    "light sensor": "light_sensor",
    "other": "other",
    "relay-switch": "relay_switch",
    "relay switch": "relay_switch",
    "relay_switch": "relay_switch",
    "scene_panel": "scene_panel",
    "scene panel": "scene_panel",
    "sensor": "sensor",
    "switch": "switch",
    "temp_control": "temp_control",
    "temp control": "temp_control",
    "灯": "light",
    "灯具": "light",
    "灯类": "light",
    "二元传感器": "binary_sensor",
    "人体传感器": "human_sensor",
    "人体感应传感器": "human_sensor",
    "传感器": "sensor",
    "光照传感器": "light_sensor",
    "开关": "switch",
    "情景面板": "scene_panel",
    "接触式传感器": "contact_sensor",
    "旋钮开关": "knob_switch",
    "温控": "temp_control",
    "温控设备": "temp_control",
    "照度传感器": "light_sensor",
    "窗帘": "curtain",
    "继电器开关": "relay_switch",
    "网关": "gateway",
    "门磁传感器": "contact_sensor",
}

__all__ = ["BROAD_CATEGORIES", "CATEGORY_ALIASES", "GENERIC_PLATFORM_CATEGORIES"]
