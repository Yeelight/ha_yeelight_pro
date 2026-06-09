"""Shared helpers for Home Assistant storage verification."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
from typing import Any

from .constants import SENSITIVE_CACHE_MARKERS, SENSITIVE_CACHE_VALUE_PATTERNS
from .report import VerificationReport


def storage_path(config_dir: Path, key: str) -> Path:
    """Return a Home Assistant storage file path."""
    return config_dir / ".storage" / key


def read_json(path: Path) -> Mapping[str, Any]:
    """Read a JSON object from disk."""
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} does not contain a JSON object")
    return data


def storage_items(config_dir: Path, key: str, item_key: str) -> list[Mapping[str, Any]]:
    """Read a Home Assistant storage list from data.<item_key>."""
    data = read_json(storage_path(config_dir, key))
    storage_data = data.get("data")
    if not isinstance(storage_data, Mapping):
        return []
    items = storage_data.get(item_key, [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping)]


def safe_storage_items(
    config_dir: Path,
    key: str,
    item_key: str,
    report: VerificationReport,
) -> list[Mapping[str, Any]] | None:
    """Read a storage item list and report sanitized failures."""
    try:
        return storage_items(config_dir, key, item_key)
    except (OSError, ValueError) as err:
        report.fail(f"storage {key} could not be read: {type(err).__name__}")
        return None


def sensitive_cache_hits(value: object) -> set[str]:
    """Return sensitive key/value markers found in cached schemas."""
    hits: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str):
                normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
                if normalized in SENSITIVE_CACHE_MARKERS:
                    hits.add(key)
            hits.update(sensitive_cache_hits(nested))
    elif isinstance(value, list):
        for item in value:
            hits.update(sensitive_cache_hits(item))
    elif isinstance(value, str):
        hits.update(
            pattern.pattern
            for pattern in SENSITIVE_CACHE_VALUE_PATTERNS
            if pattern.search(value)
        )
    return hits
