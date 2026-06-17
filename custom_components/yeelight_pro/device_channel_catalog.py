"""Product-catalog channel count helpers for Yeelight entity labels."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .capabilities.registry import product_spec
from .device_channel_semantics import component_name_key


def product_catalog_channel_count(payload: Mapping[str, Any]) -> int | None:
    """Return documented component count from Yeelight product composition."""
    spec = payload_product_spec(payload)
    if spec is None:
        return None
    if count := product_component_channel_count(spec):
        return count
    if len(spec.normal_components) != 1:
        return None
    if not is_channel_component_name(spec.normal_components[0]):
        return None
    return safe_channel_count(spec.normal_component_count)


def payload_product_spec(payload: Mapping[str, Any]) -> Any | None:
    """Return catalog product spec for the payload PID aliases."""
    return product_spec(
        payload.get("pid") or payload.get("productId") or payload.get("product_id")
    )


def product_channel_count(spec: Any) -> int | None:
    """Return documented channel count from counted or single channel components."""
    if count := product_component_channel_count(spec):
        return count
    if len(spec.normal_components) != 1:
        return None
    if not is_channel_component_name(spec.normal_components[0]):
        return None
    return safe_channel_count(spec.normal_component_count)


def product_component_channel_count(spec: Any) -> int | None:
    """Return documented channel count for known channel components only."""
    if not spec.normal_component_counts:
        return None
    switch_counts = [
        count
        for component_name, count in spec.normal_component_counts
        if is_switch_channel_component_name(component_name)
    ]
    if len(switch_counts) == 1:
        return safe_channel_count(switch_counts[0])
    counts = [
        count
        for component_name, count in spec.normal_component_counts
        if is_channel_component_name(component_name)
    ]
    if len(counts) != 1:
        return None
    return safe_channel_count(counts[0])


def is_switch_channel_component_name(value: Any) -> bool:
    """Return true for documented output switch channel component names."""
    return component_name_key(value) in {
        "switch control",
        "wireless switch channel",
        "开关",
        "无线开关通道",
    }


def is_input_channel_component_name(value: Any) -> bool:
    """Return true for documented input key/channel component names."""
    return component_name_key(value) in {
        "wireless switch channel",
        "scene control button",
        "dali scene control button",
        "无线开关通道",
        "情景按键",
        "dali情景按键",
    }


def is_channel_component_name(value: Any) -> bool:
    """Return true for documented input/output channel component names."""
    return component_name_key(value) in {
        "switch control",
        "wireless switch channel",
        "scene control button",
        "dali scene control button",
        "开关",
        "无线开关通道",
        "情景按键",
        "dali情景按键",
    }


def safe_channel_count(value: Any) -> int | None:
    """Normalize documented fixed channel counts."""
    if isinstance(value, int):
        count = value
    elif isinstance(value, str) and value.strip().isdecimal():
        count = int(value.strip())
    else:
        return None
    return count if 0 < count <= 12 else None


__all__ = [
    "is_channel_component_name",
    "is_input_channel_component_name",
    "payload_product_spec",
    "product_catalog_channel_count",
    "product_channel_count",
    "safe_channel_count",
]
