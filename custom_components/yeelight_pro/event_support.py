"""Shared helpers for Yeelight Pro event-style devices."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .utils import to_str

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_EVENT_TYPE_ALIASES = {
    "keyclick": "click",
    "key_click": "click",
    "single_click": "click",
    "longpress": "hold",
    "long_press": "hold",
    "keyhold": "hold",
    "releaseafterhold": "release_after_hold",
    "release_after_long_press": "release_after_hold",
    "keyreleaseafterlongpress": "release_after_hold",
    "freespin": "knob_spin",
    "free_spin": "knob_spin",
    "holdspin": "knob_spin",
    "hold_spin": "knob_spin",
    "knobspin": "knob_spin",
    "spin": "knob_spin",
    "rotate": "knob_spin",
    "motiontrue": "motion_detected",
    "motion_true": "motion_detected",
    "motiondetected": "motion_detected",
    "motionfalse": "motion_undetected",
    "motion_false": "motion_undetected",
    "motionundetected": "motion_undetected",
}


@dataclass(slots=True)
class YeelightRuntimeEvent:
    """Normalized runtime event delivered inside the integration."""

    source_device_id: str
    component_id: str
    event_type: str
    event_attributes: dict[str, Any]


def normalize_event_type(value: Any) -> str | None:
    """Normalize upstream event labels to stable snake_case values."""
    text = to_str(value)
    if not text:
        return None
    normalized = _NON_ALNUM_RE.sub("_", text.lower()).strip("_")
    if not normalized:
        return None
    return _EVENT_TYPE_ALIASES.get(normalized, normalized)
