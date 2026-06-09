"""Service definition verification."""

from __future__ import annotations

import ast
from pathlib import Path
import re

from .constants import DOMAIN, REQUIRED_SERVICES
from .report import VerificationReport
from .service_schema import verify_service_schema_contracts

_SERVICE_DEFINITION_RE = re.compile(r"^([a-z][a-z0-9_]*):\s*(?:#.*)?$")


def verify_services(config_dir: Path, report: VerificationReport) -> None:
    """Verify installed service definitions match runtime registrations."""
    install_root = config_dir / "custom_components" / DOMAIN
    services_path = install_root / "services.yaml"
    if not services_path.exists():
        report.fail("installed services.yaml is missing")
        return
    content = services_path.read_text(encoding="utf-8")
    definitions = _service_definitions(content)
    registrations = registered_service_names(install_root)
    failure_count = len(report.failures)

    _compare_service_sets(
        report,
        label="services.yaml definitions",
        expected=REQUIRED_SERVICES,
        actual=definitions,
    )
    _compare_service_sets(
        report,
        label="runtime service registrations",
        expected=REQUIRED_SERVICES,
        actual=registrations,
    )
    _compare_service_sets(
        report,
        label="services.yaml/runtime service alignment",
        expected=definitions,
        actual=registrations,
    )
    verify_service_schema_contracts(install_root, content, report)
    if len(report.failures) == failure_count:
        report.fact(f"service definitions/runtime registrations: {sorted(REQUIRED_SERVICES)}")
    report.metric("services", sorted(registrations))


def registered_service_names(install_root: Path) -> set[str]:
    """Return Yeelight Pro service names registered by installed Python files."""
    service_names: set[str] = set()
    for path in sorted(install_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants = _string_constants(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                service_name = _service_name_from_call(node, constants)
                if service_name is not None:
                    service_names.add(service_name)
    return service_names


def _compare_service_sets(
    report: VerificationReport,
    *,
    label: str,
    expected: set[str],
    actual: set[str],
) -> None:
    """Report missing and unexpected services for one verification layer."""
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        report.fail(f"{label} missing: {missing}")
    if unexpected:
        report.fail(f"{label} unexpected: {unexpected}")


def _service_definitions(content: str) -> set[str]:
    """Extract top-level service keys from services.yaml content."""
    return {
        match.group(1)
        for line in content.splitlines()
        if not line.startswith((" ", "\t"))
        for match in [_SERVICE_DEFINITION_RE.match(line)]
        if match is not None
    }


def _string_constants(tree: ast.Module) -> dict[str, str]:
    """Collect module-level string constants used in service registrations."""
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


def _service_name_from_call(
    node: ast.Call,
    constants: dict[str, str],
) -> str | None:
    """Extract the service name from one HA service registration call."""
    function_name = _function_name(node.func)
    if function_name == "async_register_admin_service":
        domain_arg = _positional_arg(node, 1)
        service_arg = _positional_arg(node, 2)
    elif function_name == "async_register":
        domain_arg = _positional_arg(node, 0)
        service_arg = _positional_arg(node, 1)
    else:
        return None

    if domain_arg is None or service_arg is None:
        return None
    if not _is_yeelight_domain(domain_arg, constants):
        return None
    return _string_value(service_arg, constants)


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
