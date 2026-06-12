"""Runtime capability constants for Yeelight IoT devices."""

from __future__ import annotations

LIGHT_STATE_PROPS = frozenset(
    {"p", "l", "ct", "c"}
)
FRESH_AIR_PROPS = frozenset({"vmcp", "vmcf"})
RELAY_SWITCH_PROPS = frozenset({
    "l",
    "li",
    "mock",
    "run_speed",
    "run_speed_rdy",
    "sbp",
    "slisaon",
    "slisaon_rdy",
    "sp",
})
LIGHT_SENSOR_CONFIG_PROPS = frozenset({
    "blp",
    "delay_time",
    "lumi_setting",
    "sens_range",
    "sens_shield",
})
TEMP_CONTROL_STRONG_PROPS = frozenset({
    "acp",
    "acm",
    "actt",
    "acct",
    "acf",
    "aco",
    "rfhp",
    "rfhct",
    "rfhtt",
    "tgt",
    "fa",
    "he",
    "bhm",
    "do",
    "ve",
    *FRESH_AIR_PROPS,
})
NON_LIGHT_RUNTIME_CATEGORIES = frozenset({
    "contact_sensor",
    "curtain",
    "human_sensor",
    "knob_switch",
    "light_sensor",
    "other",
    "relay_switch",
    "scene_panel",
    "temp_control",
})
SCHEMA_BROAD_CATEGORIES = frozenset({
    "binary_sensor",
    "light",
    "relay_switch",
    "sensor",
    "switch",
    "other",
})
RUNTIME_COMPONENT_CATEGORY_PRIORITY = (
    "contact_sensor",
    "light_sensor",
    "human_sensor",
    "curtain",
    "temp_control",
    "scene_panel",
    "knob_switch",
    "gateway",
    "other",
    "relay_switch",
    "light",
)
EVENT_COMPONENT_CATEGORY_PRIORITY = (
    "scene_panel",
    "knob_switch",
    "contact_sensor",
    "human_sensor",
)

__all__ = [
    "EVENT_COMPONENT_CATEGORY_PRIORITY",
    "FRESH_AIR_PROPS",
    "LIGHT_SENSOR_CONFIG_PROPS",
    "LIGHT_STATE_PROPS",
    "NON_LIGHT_RUNTIME_CATEGORIES",
    "RELAY_SWITCH_PROPS",
    "RUNTIME_COMPONENT_CATEGORY_PRIORITY",
    "SCHEMA_BROAD_CATEGORIES",
    "TEMP_CONTROL_STRONG_PROPS",
]
