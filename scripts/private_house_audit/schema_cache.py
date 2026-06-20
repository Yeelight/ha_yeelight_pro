"""Read-only product schema cache helpers for local HA audit scripts."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from custom_components.yeelight_pro.core.schema_cache import (
    STORAGE_KEY,
    product_id_from_mapping,
)
from custom_components.yeelight_pro.utils import to_int


def cached_product_schemas(config_dir: Path) -> dict[int, dict[str, Any]]:
    """Return persisted product schemas from Home Assistant ``.storage``."""
    path = config_dir / ".storage" / STORAGE_KEY
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    stored = payload.get("data") if isinstance(payload, Mapping) else None
    if not isinstance(stored, Mapping):
        stored = payload if isinstance(payload, Mapping) else {}
    schemas = stored.get("schemas")
    if not isinstance(schemas, Mapping):
        return {}
    return _normalized_schema_map(schemas)


def merge_product_schemas(
    cached: Mapping[int, Mapping[str, Any]],
    fetched: Mapping[int, Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Return fetched schemas overlaid on cached schemas."""
    merged = {int(pid): dict(schema) for pid, schema in cached.items()}
    for raw_pid, schema in fetched.items():
        if not isinstance(schema, Mapping):
            continue
        pid = to_int(raw_pid) or product_id_from_mapping(schema)
        if pid is not None:
            merged[pid] = dict(schema)
    return merged


def _normalized_schema_map(
    schemas: Mapping[Any, Any],
) -> dict[int, dict[str, Any]]:
    """Normalize persisted schema keys to integer product ids."""
    result: dict[int, dict[str, Any]] = {}
    for raw_pid, schema in schemas.items():
        if not isinstance(schema, Mapping):
            continue
        pid = to_int(raw_pid) or product_id_from_mapping(schema)
        if pid is not None:
            result[pid] = dict(schema)
    return result


__all__ = ["cached_product_schemas", "merge_product_schemas"]
