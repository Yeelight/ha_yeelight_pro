"""Yeelight Pro 属性能力映射表兼容入口."""
from __future__ import annotations

from .models import PropertyCapability
from .registry import iot_registry, property_capability

_REGISTRY = iot_registry()

PROPERTY_CAPABILITIES: dict[str, PropertyCapability] = dict(_REGISTRY.property_capabilities)

__all__ = ["PROPERTY_CAPABILITIES", "PropertyCapability", "property_capability"]
