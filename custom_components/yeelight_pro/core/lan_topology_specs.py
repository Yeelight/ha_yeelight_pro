"""Documented LAN topology type defaults used by payload normalization."""

from __future__ import annotations

from typing import Any

NODE_TYPE_ROOM = 1
NODE_TYPE_DEVICE = 2
NODE_TYPE_AREA = 3
NODE_TYPE_GROUP = 4
NODE_TYPE_HOUSE = 5
NODE_TYPE_SCENE = 6

_LIGHT_PARAMS: dict[int, dict[str, Any]] = {
    1: {"p": False},
    2: {"p": False, "l": 100},
    3: {"p": False, "l": 100, "ct": 4000},
    4: {"p": False, "l": 100, "ct": 4000, "c": 0xFFFFFF, "m": 2},
    14: {"p": False, "l": 100, "ct": 4000},
}
_BATH_HEATER_PARAMS: dict[str, Any] = {
    "p": False,
    "bhm": 1,
    "do": 1,
    "ve": 0,
    "fa": 0,
    "he": 0,
    "tgt": 26,
    "t": 26,
}
AC_PARAMS: dict[str, Any] = {
    "acp": False,
    "acm": 1,
    "actt": 26,
    "acct": 26,
    "acf": 4,
}
AC_PROPERTIES: tuple[dict[str, str], ...] = (
    {"propId": "acp", "access": "read_write"},
    {"propId": "acm", "access": "read_write"},
    {"propId": "actt", "access": "read_write"},
    {"propId": "acct", "access": "read_only"},
    {"propId": "acf", "access": "read_write"},
)
LAN_TYPE_SPECS: dict[int, dict[str, Any]] = {
    1: {"category": "light", "model": "开关灯", "params": _LIGHT_PARAMS[1]},
    2: {"category": "light", "model": "亮度灯", "params": _LIGHT_PARAMS[2]},
    3: {"category": "light", "model": "色温灯", "params": _LIGHT_PARAMS[3]},
    4: {"category": "light", "model": "彩光灯", "params": _LIGHT_PARAMS[4]},
    6: {"category": "curtain", "model": "窗帘", "params": {"cp": 0, "tp": 0}},
    7: {"category": "relay_switch", "model": "继电器开关", "switch_prop": "p", "channels": 2},
    10: {
        "category": "temp_control",
        "model": "空调网关",
        "params": AC_PARAMS,
        "indexed_ac_channels": True,
    },
    13: {"category": "relay_switch", "model": "继电器开关", "switch_prop": "sp"},
    14: {"category": "light", "model": "色温灯", "params": _LIGHT_PARAMS[14]},
    15: {"category": "temp_control", "model": "空调控制器", "params": AC_PARAMS},
    128: {
        "category": "scene_panel",
        "model": "情景面板",
        "events": ("click", "hold", "release_after_hold"),
    },
    129: {
        "category": "human_sensor",
        "model": "人体传感器",
        "params": {"mv": False},
        "events": ("motion_detected", "motion_undetected"),
    },
    130: {
        "category": "contact_sensor",
        "model": "门磁传感器",
        "params": {"dc": False, "alm": False},
        "events": ("door_open", "door_close", "door_alarm", "door_normal"),
    },
    132: {"category": "knob_switch", "model": "旋钮开关", "events": ("knob_spin",)},
    134: {
        "category": "light_sensor",
        "model": "照度传感器",
        "params": {"mv": False, "level": 0},
        "events": ("motion_detected", "motion_undetected"),
    },
    135: {"category": "light_sensor", "model": "照度传感器", "params": {"luminance": 0}},
    136: {"category": "other", "model": "温湿度传感器", "params": {"t": 0, "h": 0}},
    138: {
        "category": "human_sensor",
        "model": "人体传感器",
        "params": {"mv": False, "luminance": 0},
        "events": (
            "motion_detected",
            "motion_undetected",
            "human_enter",
            "human_leave",
        ),
    },
    2049: {
        "category": "temp_control",
        "model": "浴霸加热器",
        "params": _BATH_HEATER_PARAMS,
    },
    2052: {"category": "other", "model": "TOF传感器", "events": ("handwave",)},
}
