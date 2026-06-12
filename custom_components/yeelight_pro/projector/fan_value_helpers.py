"""Fan value conversion helpers for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.util.percentage import ranged_value_to_percentage

from ..utils import to_int
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


def raw_prop(prop_key: str | None) -> str | None:
    """Return the raw vendor property id for a possibly indexed control key."""
    if prop_key is None:
        return None
    return prop_key.split("-", 1)[1] if "-" in prop_key else prop_key
