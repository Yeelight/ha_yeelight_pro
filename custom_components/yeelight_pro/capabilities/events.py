"""Yeelight Pro 事件类型归一化兼容入口."""
from __future__ import annotations

from .registry import iot_registry, normalize_event_type

_REGISTRY = iot_registry()

EVENT_TYPE_ALIASES: dict[str | int, str] = dict(_REGISTRY.event_aliases)

__all__ = ["EVENT_TYPE_ALIASES", "normalize_event_type"]
