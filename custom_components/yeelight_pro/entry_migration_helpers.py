"""Shared primitive helpers for config-entry migration."""

from __future__ import annotations

from typing import Any, Mapping


def mapping_or_empty(value: Any) -> dict[str, Any]:
    """Return a plain dict for mapping-like values."""
    return dict(value) if isinstance(value, Mapping) else {}


def first_value(value: Mapping[str, Any], *keys: str) -> Any:
    """Return the first non-empty value for a set of legacy keys."""
    for key in keys:
        candidate = value.get(key)
        if candidate not in (None, ""):
            return candidate
    return None


def coerce_house_id(value: Any) -> int | str:
    """Coerce numeric house identifiers while preserving non-numeric ids."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return string_value(value)


def optional_int(value: Any) -> int | None:
    """Return an integer or None for optional numeric fields."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def coerce_int(
    value: Any,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Coerce an integer with optional bounds and a safe default."""
    if isinstance(value, bool):
        return default
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def coerce_bool(value: Any, *, default: bool) -> bool:
    """Coerce common string booleans while preserving a default for None."""
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    return bool(value)


def string_value(value: Any) -> str:
    """Return an empty string for None, otherwise str(value)."""
    return "" if value is None else str(value)


__all__ = [
    "coerce_bool",
    "coerce_house_id",
    "coerce_int",
    "first_value",
    "mapping_or_empty",
    "optional_int",
    "string_value",
]
