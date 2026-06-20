"""Diagnostics-safe JSON frame shape helpers for Yeelight Pro push transport."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import blake2b
from typing import Any

_MAX_SHAPE_DEPTH = 3
_MAX_SHAPE_OBJECTS = 8
_MAX_SHAPE_KEYS = 16
_NESTED_MAPPING_KEYS = ("data", "params", "result")
_SHAPE_FLAG_KEYS = ("type", "method", "nodes", "data", "params", "result")


def payload_shape_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return field-name-only JSON shape details without copying values."""
    return {
        "objects": _shape_objects(payload, path="root", depth=0, remaining=[]),
        "status": _status_shape(payload),
    }


def _shape_objects(
    payload: Mapping[str, Any],
    *,
    path: str,
    depth: int,
    remaining: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collect nested object shapes through known envelope keys."""
    if len(remaining) >= _MAX_SHAPE_OBJECTS:
        return remaining
    remaining.append(
        {
            "path": path,
            "keys": _safe_keys(payload),
            "flags": {key: key in payload for key in _SHAPE_FLAG_KEYS},
        }
    )
    if depth >= _MAX_SHAPE_DEPTH:
        return remaining
    for key in _NESTED_MAPPING_KEYS:
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            _shape_objects(
                nested,
                path=f"{path}.{key}",
                depth=depth + 1,
                remaining=remaining,
            )
            if len(remaining) >= _MAX_SHAPE_OBJECTS:
                return remaining
    return remaining


def _safe_keys(payload: Mapping[str, Any]) -> list[str]:
    """Return stable key names only, never corresponding values."""
    return sorted(str(key) for key in payload)[:_MAX_SHAPE_KEYS]


def _status_shape(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return redacted status text metadata for method-less non-data frames."""
    if payload.get("method") not in (None, "") or "type" in payload:
        return None
    result = payload.get("result")
    if not isinstance(result, str):
        return None
    data = payload.get("data")
    return {
        "result_length": len(result),
        "result_hash": _safe_digest(result),
        "data_keys": _safe_keys(data) if isinstance(data, Mapping) else [],
    }


def _safe_digest(value: str) -> str:
    """Return a stable non-reversible digest for low-cardinality diagnostics."""
    digest = blake2b(digest_size=6)
    digest.update(value.encode("utf-8", errors="replace"))
    return digest.hexdigest()


__all__ = ["payload_shape_summary"]
