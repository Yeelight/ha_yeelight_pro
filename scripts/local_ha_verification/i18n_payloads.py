"""Translation payload helpers for local HA verification."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from .report import VerificationReport


def read_translation_payloads(
    install_root: Path,
    translation_files: tuple[str, ...],
    report: VerificationReport,
) -> dict[str, dict[str, Any]]:
    """Read installed translation JSON payloads without importing HA."""
    payloads: dict[str, dict[str, Any]] = {}
    for relative_path in translation_files:
        path = install_root / relative_path
        if not path.exists():
            report.fail(f"installed translation file is missing: {relative_path}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            report.fail(f"invalid translation JSON in {relative_path}: {err}")
            continue
        if not isinstance(payload, dict):
            report.fail(f"translation JSON must be an object: {relative_path}")
            continue
        payloads[relative_path] = payload
    return payloads


def leaf_paths(value: object, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    """Return leaf key paths from a nested translation payload."""
    if not isinstance(value, Mapping):
        return {prefix}
    paths: set[tuple[str, ...]] = set()
    for key, child in value.items():
        paths.update(leaf_paths(child, (*prefix, str(key))))
    return paths


def mapping_at(payload: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any]:
    """Return a nested mapping or an empty mapping when absent."""
    current: object = payload
    for key in path:
        if not isinstance(current, Mapping):
            return {}
        current = current.get(key)
    if isinstance(current, Mapping):
        return current
    return {}


def value_at(payload: Mapping[str, Any], path: tuple[str, ...]) -> object:
    """Return a nested value or None when absent."""
    current: object = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def format_paths(paths: list[tuple[str, ...]]) -> list[str]:
    """Format key paths for compact failure output."""
    return [format_path(path) for path in paths[:10]]


def format_path(path: tuple[str, ...]) -> str:
    """Format one translation key path."""
    return ".".join(path)
