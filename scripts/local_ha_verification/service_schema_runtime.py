"""Runtime service schema AST helpers."""

from __future__ import annotations

import ast
from pathlib import Path

from .constants import DOMAIN


def registered_service_schema_fields(
    install_root: Path,
) -> dict[str, dict[str, bool]]:
    """Return runtime service schema fields keyed by service name."""
    constants = _all_string_constants(install_root)
    schema_by_name: dict[str, dict[str, bool]] = {}
    service_schemas: dict[str, dict[str, bool]] = {}

    for path in sorted(install_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_constants = {**constants, **_string_constants(tree)}
        schema_by_name.update(_schema_fields_by_name(tree, module_constants))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            service_name, schema_name = _service_schema_from_call(
                node,
                module_constants,
            )
            if service_name is None or schema_name is None:
                continue
            service_schemas[service_name] = schema_by_name.get(schema_name, {})
    return service_schemas


def _all_string_constants(install_root: Path) -> dict[str, str]:
    """Collect string constants across installed integration modules."""
    constants: dict[str, str] = {}
    for path in sorted(install_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants.update(_string_constants(tree))
    return constants


def _schema_fields_by_name(
    tree: ast.Module,
    constants: dict[str, str],
) -> dict[str, dict[str, bool]]:
    """Extract module-level vol.Schema field declarations."""
    schemas: dict[str, dict[str, bool]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        schema_fields = _schema_fields(node.value, constants)
        if schema_fields is None:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                schemas[target.id] = schema_fields
    return schemas


def _schema_fields(
    node: ast.expr,
    constants: dict[str, str],
) -> dict[str, bool] | None:
    """Extract required flags from a vol.Schema({...}) expression."""
    if not isinstance(node, ast.Call) or _function_name(node.func) != "Schema":
        return None
    schema_dict = _positional_arg(node, 0)
    if not isinstance(schema_dict, ast.Dict):
        return None

    fields: dict[str, bool] = {}
    for key_node in schema_dict.keys:
        if key_node is None:
            continue
        field_name, required = _field_contract_from_schema_key(key_node, constants)
        if field_name is not None:
            fields[field_name] = required
    return fields


def _field_contract_from_schema_key(
    node: ast.expr,
    constants: dict[str, str],
) -> tuple[str | None, bool]:
    """Resolve a vol.Required/vol.Optional schema key."""
    if not isinstance(node, ast.Call):
        return (_string_value(node, constants), True)
    key_type = _function_name(node.func)
    if key_type not in {"Required", "Optional"}:
        return (None, False)
    field_arg = _positional_arg(node, 0)
    if field_arg is None:
        return (None, key_type == "Required")
    return (_string_value(field_arg, constants), key_type == "Required")


def _service_schema_from_call(
    node: ast.Call,
    constants: dict[str, str],
) -> tuple[str | None, str | None]:
    """Extract service name and schema variable from an HA registration call."""
    function_name = _function_name(node.func)
    if function_name == "async_register_admin_service":
        domain_arg = _positional_arg(node, 1)
        service_arg = _positional_arg(node, 2)
    elif function_name == "async_register":
        domain_arg = _positional_arg(node, 0)
        service_arg = _positional_arg(node, 1)
    else:
        return (None, None)

    if domain_arg is None or service_arg is None:
        return (None, None)
    if not _is_yeelight_domain(domain_arg, constants):
        return (None, None)
    schema_name = _schema_keyword_name(node)
    return (_string_value(service_arg, constants), schema_name)


def _schema_keyword_name(node: ast.Call) -> str | None:
    """Return the schema keyword variable name from a service registration."""
    for keyword in node.keywords:
        if keyword.arg == "schema" and isinstance(keyword.value, ast.Name):
            return keyword.value.id
    return None


def _string_constants(tree: ast.Module) -> dict[str, str]:
    """Collect module-level string constants."""
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(
            node.value.value,
            str,
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                constants[target.id] = node.value.value
    return constants


def _function_name(node: ast.expr) -> str | None:
    """Return the called function or method name."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _positional_arg(node: ast.Call, index: int) -> ast.expr | None:
    """Return a positional argument if it exists."""
    if len(node.args) <= index:
        return None
    return node.args[index]


def _is_yeelight_domain(node: ast.expr, constants: dict[str, str]) -> bool:
    """Return true when a service registration targets this integration."""
    if isinstance(node, ast.Name) and node.id == "DOMAIN":
        return True
    return _string_value(node, constants) == DOMAIN


def _string_value(node: ast.expr, constants: dict[str, str]) -> str | None:
    """Resolve a literal or module-level constant string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None
