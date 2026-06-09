"""运行时产品模型推断模板。"""

from __future__ import annotations

from typing import Any, Final
import re

# 默认范围元组格式：(min, max, step)。
DEFAULT_BRIGHTNESS_RANGE: Final = (1, 100, 1)
DEFAULT_COLOR_TEMP_RANGE_KELVIN: Final = (2700, 6500, None)

# 索引式开关键匹配正则：形如 "1-p", "2-sp"。
INDEXED_SWITCH_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<index>\d+)-(?P<prop>p|sp)$"
)

# 运行时属性模板只服务于无官方 product schema 时的保守推断。
RUNTIME_PROPERTY_TEMPLATES: Final[dict[str, dict[str, dict[str, Any]]]] = {
    "light": {
        "p": {
            "name": "开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
        "sp": {
            "name": "软开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
        "l": {
            "name": "亮度",
            "kind": "control",
            "property_type": "apply",
            "format": "uint8",
            "unit": "%",
            "access": "read_write",
            "value_range": DEFAULT_BRIGHTNESS_RANGE,
        },
        "ct": {
            "name": "色温",
            "kind": "control",
            "property_type": "apply",
            "format": "uint16",
            "unit": "kelvin",
            "access": "read_write",
            "value_range": DEFAULT_COLOR_TEMP_RANGE_KELVIN,
        },
        "c": {
            "name": "颜色",
            "kind": "control",
            "property_type": "apply",
            "format": "uint32",
            "access": "read_write",
        },
        "m": {
            "name": "模式",
            "kind": "state",
            "property_type": "apply",
            "format": "uint8",
            "access": "read_write",
        },
    },
    "fan": {
        "p": {
            "name": "开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
        "lv": {
            "name": "风速",
            "kind": "control",
            "property_type": "apply",
            "format": "uint8",
            "access": "read_write",
        },
        "dir": {
            "name": "风向",
            "kind": "control",
            "property_type": "apply",
            "format": "string",
            "access": "read_write",
        },
        "m": {
            "name": "模式",
            "kind": "control",
            "property_type": "apply",
            "format": "string",
            "access": "read_write",
        },
    },
    "switch": {
        "p": {
            "name": "开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
        "sp": {
            "name": "软开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
        "on": {
            "name": "开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
    },
    "cover": {
        "cp": {
            "name": "当前位置",
            "kind": "state",
            "property_type": "apply",
            "format": "uint8",
            "unit": "%",
            "access": "read_only",
        },
        "tp": {
            "name": "目标位置",
            "kind": "control",
            "property_type": "apply",
            "format": "uint8",
            "unit": "%",
            "access": "read_write",
        },
    },
    "binary_sensor": {
        "mv": {
            "name": "人体移动",
            "kind": "state",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_only",
        },
        "dc": {
            "name": "门窗状态",
            "kind": "state",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_only",
        },
        "alm": {
            "name": "防拆",
            "kind": "state",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_only",
        },
    },
    "sensor": {
        "t": {
            "name": "温度",
            "kind": "state",
            "property_type": "apply",
            "format": "float",
            "unit": "°C",
            "access": "read_only",
        },
        "h": {
            "name": "湿度",
            "kind": "state",
            "property_type": "apply",
            "format": "float",
            "unit": "%",
            "access": "read_only",
        },
        "luminance": {
            "name": "照度",
            "kind": "state",
            "property_type": "apply",
            "format": "float",
            "unit": "lx",
            "access": "read_only",
        },
        "level": {
            "name": "等级",
            "kind": "state",
            "property_type": "apply",
            "format": "int",
            "access": "read_only",
        },
    },
    "climate": {
        "acm": {
            "name": "模式",
            "kind": "control",
            "property_type": "apply",
            "format": "uint8",
            "access": "read_write",
        },
        "actt": {
            "name": "目标温度",
            "kind": "control",
            "property_type": "apply",
            "format": "float",
            "unit": "°C",
            "access": "read_write",
        },
        "acct": {
            "name": "当前温度",
            "kind": "state",
            "property_type": "apply",
            "format": "float",
            "unit": "°C",
            "access": "read_only",
        },
        "acf": {
            "name": "风速",
            "kind": "control",
            "property_type": "apply",
            "format": "uint8",
            "access": "read_write",
        },
        "aco": {
            "name": "开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
    },
    "lock": {
        "lock": {
            "name": "门锁",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
        "locked": {
            "name": "门锁状态",
            "kind": "state",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_only",
        },
        "lck": {
            "name": "门锁状态",
            "kind": "state",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_only",
        },
    },
}
