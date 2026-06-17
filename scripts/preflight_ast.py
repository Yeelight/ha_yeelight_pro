"""Shared AST helpers for no-runtime preflight checks."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def literal_client_capability_flags(component_root: Path) -> dict[str, Any] | None:
    """Read literal diagnostics capability flags without importing HA runtime."""
    path = component_root / "diagnostic_runtime.py"
    flags = _literal_client_capability_flags_from_path(
        path,
        "client_capabilities_for_entry",
    )
    if flags is not None:
        return flags
    return _literal_client_capability_flags_from_path(
        component_root / "diagnostics.py",
        "_client_capabilities_for_entry",
    )


def _literal_client_capability_flags_from_path(
    path: Path,
    function_name: str,
) -> dict[str, Any] | None:
    """Read literal capability flags from one source module."""
    if not path.exists():
        return None

    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != function_name:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                return _literal_string_dict(child.value)
    return None


def _literal_string_dict(node: ast.Dict) -> dict[str, Any]:
    """Return string-key literal values from an AST dict expression."""
    values: dict[str, Any] = {}
    for key_node, value_node in zip(node.keys, node.values, strict=False):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            continue
        try:
            values[key_node.value] = ast.literal_eval(value_node)
        except (TypeError, ValueError):
            continue
    return values
