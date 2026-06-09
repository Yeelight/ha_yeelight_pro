"""Yeelight Pro IoT 品类和组件到 Home Assistant 平台的兼容入口."""
from __future__ import annotations

from .registry import component_platform_hint, iot_registry, platform_for_category

_REGISTRY = iot_registry()

CATEGORY_PLATFORM_MAP: dict[str, str] = dict(_REGISTRY.category_platform_map)
COMPONENT_PLATFORM_HINTS: dict[str, str] = dict(_REGISTRY.component_platform_hints)


__all__ = [
    "CATEGORY_PLATFORM_MAP",
    "COMPONENT_PLATFORM_HINTS",
    "component_platform_hint",
    "platform_for_category",
]
