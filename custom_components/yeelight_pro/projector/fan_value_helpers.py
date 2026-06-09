"""Fan value conversion helpers for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.fan import DIRECTION_FORWARD, DIRECTION_REVERSE
from homeassistant.util.percentage import ranged_value_to_percentage

from ..utils import to_int, to_str
from .common import NumericRange


def project_fan_percentage(
    state: Mapping[str, Any],
    speed_key: str | None,
    speed_range: NumericRange | None,
) -> int | None:
    """Project a vendor fan speed value into a Home Assistant percentage."""
    if speed_key is None:
        return None

    raw_key = raw_prop(speed_key)
    if raw_key is None:
        return None
    raw = to_int(state.get(raw_key))
    if raw is None:
        return None

    if speed_range is None:
        return max(0, min(100, raw))

    minimum = speed_range.min if speed_range.min is not None else 1
    maximum = speed_range.max if speed_range.max is not None else 100
    if maximum < minimum:
        return max(0, min(100, raw))
    if minimum == 0 and raw == 0:
        return 0
    if raw <= 0:
        return 0
    return int(round(ranged_value_to_percentage((minimum, maximum), raw)))


def fan_speed_count(speed_range: NumericRange | None) -> int:
    """Return the Home Assistant speed count implied by a vendor range."""
    if speed_range is None:
        return 100

    minimum = speed_range.min if speed_range.min is not None else 1
    maximum = speed_range.max if speed_range.max is not None else 100
    step = speed_range.step if speed_range.step is not None and speed_range.step > 0 else 1
    if maximum < minimum:
        return 100
    return max(1, int(((maximum - minimum) / step) + 1))


def enum_codes(value: Any) -> list[str]:
    """Return stable enum codes from vendor constraint payloads."""
    items: list[str] = []
    if isinstance(value, Mapping):
        for key in ("values", "value_list", "valueList", "enum"):
            items.extend(enum_codes(value.get(key)))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                code = to_str(item.get("code", item.get("value", item.get("id"))))
                if code:
                    items.append(code)
            else:
                text = to_str(item)
                if text:
                    items.append(text)
    return items


def direction_values_from_constraint(value: Any) -> dict[str, Any]:
    """Map vendor constraint enum values to Home Assistant directions."""
    mapping: dict[str, Any] = {}
    for item in enum_items(value):
        raw_value = item.get("code", item.get("value", item.get("id")))
        direction = to_ha_direction(raw_value, {})
        if direction is None:
            direction = to_ha_direction(item.get("desc", item.get("name")), {})
        if direction is None or raw_value is None:
            continue
        mapping[direction] = raw_value
    return mapping


def direction_values_from_value_list(value_list: list[Any]) -> dict[str, Any]:
    """Map canonical product value-list items to Home Assistant directions."""
    mapping: dict[str, Any] = {}
    for item in value_list:
        raw_value = getattr(item, "code", None)
        direction = to_ha_direction(raw_value, {})
        if direction is None:
            direction = to_ha_direction(getattr(item, "desc", None), {})
        if direction is None or raw_value is None:
            continue
        mapping[direction] = raw_value
    return mapping


def enum_items(value: Any) -> list[Mapping[str, Any]]:
    """Return enum item mappings from vendor constraint payloads."""
    items: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        for key in ("values", "value_list", "valueList", "enum"):
            items.extend(enum_items(value.get(key)))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                items.append(item)
    return items


def to_ha_direction(value: Any, direction_values: Mapping[str, Any]) -> str | None:
    """Convert vendor direction values into Home Assistant direction constants."""
    if value is None:
        return None

    for direction, raw_value in direction_values.items():
        if value == raw_value or to_str(value) == to_str(raw_value):
            return direction

    text = to_str(value)
    if not text:
        return None

    normalized = text.lower().replace("-", "_").replace(" ", "_")
    if normalized in {"0", "forward", "fwd", "clockwise", "cw", "zheng", "zhengzhuan", "正转"}:
        return DIRECTION_FORWARD
    if normalized in {"1", "reverse", "rev", "counterclockwise", "ccw", "fan_reverse", "fanzhuan", "反转"}:
        return DIRECTION_REVERSE
    return None


def raw_prop(prop_key: str | None) -> str | None:
    """Return the raw vendor property id for a possibly indexed control key."""
    if prop_key is None:
        return None
    return prop_key.split("-", 1)[1] if "-" in prop_key else prop_key
