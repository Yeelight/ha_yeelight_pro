"""Small value-normalization helpers for private-house reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def int_value(value: Any) -> int:
    """Return an int diagnostics value without treating bools as integers."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def has_int_value(device: Mapping[str, Any], key: str) -> bool:
    """Return whether an integer diagnostics field is present."""
    value = device.get(key)
    return isinstance(value, int) and not isinstance(value, bool)


def mapping_value(value: Any) -> Mapping[str, Any]:
    """Return mapping diagnostics or an empty mapping."""
    return value if isinstance(value, Mapping) else {}


def sequence_value(value: Any) -> Sequence[Any]:
    """Return sequence diagnostics or an empty tuple, excluding strings."""
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()
