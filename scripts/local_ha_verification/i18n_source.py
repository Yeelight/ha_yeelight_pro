"""Installed source parsers for local HA i18n verification."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path


def installed_option_translation_keys(install_root: Path) -> set[str]:
    """Return option keys visible in the installed options schema."""
    const_path = install_root / "const.py"
    helper_paths = (
        install_root / "config_flow_options.py",
        install_root / "device_filter_options.py",
    )
    if not const_path.exists():
        return set()

    const_constants = _string_constants(
        ast.parse(const_path.read_text(encoding="utf-8"))
    )
    keys: set[str] = set()
    for path in helper_paths:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = {**const_constants, **_string_constants(tree)}
        keys.update(
            value
            for call in ast.walk(tree)
            if isinstance(call, ast.Call)
            for value in [_schema_key_value(call, constants)]
            if value is not None
        )
    return keys


def installed_selector_option_translation_paths(
    install_root: Path,
) -> set[tuple[str, ...]]:
    """Return selector option translation paths required by installed forms."""
    const_path = install_root / "const.py"
    helper_paths = (
        install_root / "config_flow_helpers.py",
        install_root / "config_flow_options.py",
        install_root / "device_filter_options.py",
    )
    if not const_path.exists():
        return set()

    const_constants = _string_constants(
        ast.parse(const_path.read_text(encoding="utf-8"))
    )
    paths: set[tuple[str, ...]] = set()
    for path in helper_paths:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = {**const_constants, **_string_constants(tree)}
        paths.update(_selector_translation_paths(tree, constants))
    return paths


def installed_repair_placeholder_keys(install_root: Path) -> set[str]:
    """Return topology Repairs placeholders from installed repair_issues.py."""
    path = install_root / "repair_issues.py"
    if not path.exists():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        if _function_name(call.func) != "async_create_issue":
            continue
        for keyword in call.keywords:
            if keyword.arg == "translation_placeholders":
                return _placeholder_keys(keyword.value)
    return set()


def _placeholder_keys(node: ast.expr) -> set[str]:
    """Extract string keys from a translation_placeholders expression."""
    if isinstance(node, ast.Dict):
        return {
            key.value
            for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
    if isinstance(node, ast.DictComp):
        return _dict_keys_from_comprehension(node)
    return set()


def _dict_keys_from_comprehension(node: ast.DictComp) -> set[str]:
    """Extract literal source-dict keys from a simple dict comprehension."""
    keys: set[str] = set()
    for generator in node.generators:
        call = generator.iter
        if not isinstance(call, ast.Call):
            continue
        if _function_name(call.func) != "items":
            continue
        source_dict = _method_owner(call.func)
        if not isinstance(source_dict, ast.Dict):
            continue
        for key in source_dict.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
    return keys


def _calls_in_function(tree: ast.Module, function_name: str) -> list[ast.Call]:
    """Return calls inside one module-level function."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return [child for child in ast.walk(node) if isinstance(child, ast.Call)]
    return []


def _schema_key_value(
    node: ast.Call,
    constants: Mapping[str, str],
) -> str | None:
    """Resolve vol.Required/Optional first argument to a translation key."""
    if _function_name(node.func) not in {"Required", "Optional"}:
        return None
    if not node.args:
        return None
    first_arg = node.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return first_arg.value
    if isinstance(first_arg, ast.Name):
        return constants.get(first_arg.id)
    return None


def _selector_translation_paths(
    tree: ast.Module,
    constants: Mapping[str, str],
) -> set[tuple[str, ...]]:
    """Return required translation paths for select selector option labels."""
    paths: set[tuple[str, ...]] = set()
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        if _function_name(call.func) != "SelectSelectorConfig":
            continue
        translation_key = _keyword_string(call, "translation_key", constants)
        if translation_key is None:
            continue
        for option in _keyword_string_list(call, "options", constants):
            paths.add(("selector", translation_key, "options", option))
    return paths


def _keyword_string(
    call: ast.Call,
    name: str,
    constants: Mapping[str, str],
) -> str | None:
    """Resolve one string keyword argument."""
    for keyword in call.keywords:
        if keyword.arg == name:
            return _string_value(keyword.value, constants)
    return None


def _keyword_string_list(
    call: ast.Call,
    name: str,
    constants: Mapping[str, str],
) -> set[str]:
    """Resolve one keyword argument that contains a literal string list."""
    for keyword in call.keywords:
        if keyword.arg != name:
            continue
        value = keyword.value
        if not isinstance(value, (ast.List, ast.Tuple)):
            return set()
        return {
            text
            for item in value.elts
            if (text := _string_value(item, constants)) is not None
        }
    return set()


def _string_value(
    node: ast.expr,
    constants: Mapping[str, str],
) -> str | None:
    """Resolve a string literal or simple module constant."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _string_constants(tree: ast.Module) -> dict[str, str]:
    """Collect module-level string constants."""
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                constants[target.id] = node.value.value
    return constants


def _function_name(node: ast.expr) -> str | None:
    """Return a called function or method name."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _method_owner(node: ast.expr) -> ast.expr | None:
    """Return the owner expression for a method call."""
    if isinstance(node, ast.Attribute):
        return node.value
    return None
