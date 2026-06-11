"""运行时模板共享常量。"""

from __future__ import annotations

from typing import Final

# 默认范围元组格式：(min, max, step)。
DEFAULT_BRIGHTNESS_RANGE: Final = (1, 100, 1)
DEFAULT_COLOR_TEMP_RANGE_KELVIN: Final = (2700, 6500, None)

