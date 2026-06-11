"""运行时产品模型推断模板 facade。"""

from __future__ import annotations

from typing import Any, Final
import re

from .runtime_template_constants import (
    DEFAULT_BRIGHTNESS_RANGE,
    DEFAULT_COLOR_TEMP_RANGE_KELVIN,
)
from .runtime_template_controls import RUNTIME_CONTROL_TEMPLATES
from .runtime_template_hvac import RUNTIME_HVAC_TEMPLATES
from .runtime_template_sensors import RUNTIME_SENSOR_TEMPLATES

# 索引式开关键匹配正则：形如 "1-p", "2-sp"。
INDEXED_SWITCH_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<index>\d+)-(?P<prop>p|sp)$"
)

# 运行时属性模板只服务于无官方 product schema 时的保守推断。
RUNTIME_PROPERTY_TEMPLATES: Final[dict[str, dict[str, dict[str, Any]]]] = {
    **RUNTIME_CONTROL_TEMPLATES,
    **RUNTIME_SENSOR_TEMPLATES,
    **RUNTIME_HVAC_TEMPLATES,
}

__all__ = [
    "DEFAULT_BRIGHTNESS_RANGE",
    "DEFAULT_COLOR_TEMP_RANGE_KELVIN",
    "INDEXED_SWITCH_KEY_RE",
    "RUNTIME_PROPERTY_TEMPLATES",
]
