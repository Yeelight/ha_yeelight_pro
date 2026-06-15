"""Shared helpers for Yeelight Pro light control calls."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

try:
    from homeassistant.components.light import ATTR_TRANSITION
except ImportError:  # pragma: no cover - 兼容旧版 HA
    ATTR_TRANSITION = "transition"

MAX_TRANSITION_DURATION_MS = 3_600_000


def transition_duration_ms(kwargs: Mapping[str, Any]) -> int | None:
    """Return HA transition seconds as Yeelight duration milliseconds."""
    if ATTR_TRANSITION not in kwargs:
        return None

    try:
        seconds = float(kwargs[ATTR_TRANSITION])
    except (TypeError, ValueError):
        return None

    if not isfinite(seconds):
        return None
    milliseconds = int(round(seconds * 1000))
    return max(0, min(MAX_TRANSITION_DURATION_MS, milliseconds))


__all__ = [
    "MAX_TRANSITION_DURATION_MS",
    "transition_duration_ms",
]
