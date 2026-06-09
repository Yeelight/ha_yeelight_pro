"""Diagnostics-specific release preflight checks for Yeelight Pro."""

from __future__ import annotations

from pathlib import Path

from scripts.hacs_preflight_data import (
    DIAGNOSTICS_CONTRACT_TEST_TOKENS,
    DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES,
    DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES,
    DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES,
)
from scripts.preflight_ast import literal_client_capability_flags


def check_diagnostics_contracts(component_root: Path) -> list[str]:
    """Ensure diagnostics redaction and capability boundaries stay covered."""
    errors = _check_diagnostics_contract_tests(component_root)
    errors.extend(_check_client_capability_flags(component_root))
    return errors


def _check_diagnostics_contract_tests(component_root: Path) -> list[str]:
    """Ensure diagnostics contract tests still assert aggregate safe output."""
    errors: list[str] = []
    tests_root = component_root / "tests"
    for relative_path, required_tokens in DIAGNOSTICS_CONTRACT_TEST_TOKENS.items():
        path = tests_root / Path(relative_path).name
        if not path.exists():
            errors.append(f"diagnostics redaction requires {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"{relative_path} missing {reason}: {token}")
    return errors


def _check_client_capability_flags(component_root: Path) -> list[str]:
    """Block accidental release of unverified live connection capabilities."""
    capability_flags = literal_client_capability_flags(component_root)
    if capability_flags is None:
        return ["diagnostics.py must expose literal client capability flags"]

    errors: list[str] = []
    for key in DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES:
        if capability_flags.get(key) is not True:
            errors.append(f"diagnostics.py client capability must remain true: {key}")
    for key in DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES:
        if capability_flags.get(key) is not False:
            errors.append(f"diagnostics.py live capability must remain false: {key}")
    for key, reason in DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES.items():
        if key in capability_flags:
            errors.append(f"diagnostics.py forbidden client capability {key}: {reason}")
    return errors
