"""运行时温控与安全类属性模板。"""

from __future__ import annotations

from typing import Any, Final

RUNTIME_HVAC_TEMPLATES: Final[dict[str, dict[str, dict[str, Any]]]] = {
    "fresh_air": {
        "vmcp": {
            "name": "新风开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
        "vmcf": {
            "name": "新风风速",
            "kind": "control",
            "property_type": "apply",
            "format": "uint8",
            "access": "read_write",
            "value_range": (1, 100, 1),
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
            "name": "在线",
            "kind": "state",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_only",
        },
    },
    "temp_control": {
        "acp": {
            "name": "空调开关",
            "kind": "control",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_write",
        },
        "aco": {
            "name": "在线",
            "kind": "state",
            "property_type": "apply",
            "format": "boolean",
            "access": "read_only",
        },
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
    },
}
