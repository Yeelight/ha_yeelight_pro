"""Installed diagnostics capability verification."""

from __future__ import annotations

import ast
from pathlib import Path

from scripts.hacs_preflight_data import (
    DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES,
    DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES,
    DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES,
)
from scripts.preflight_ast import literal_client_capability_flags

from .constants import DOMAIN
from .diagnostics_websocket import verify_websocket_event_runtime_contract
from .report import VerificationReport

REQUIRED_OPTION_STATUS_FIELDS = {
    "analytics_retention_days",
    "analytics_runtime_enabled",
    "debug_mode_enabled",
    "live_updates_enabled",
    "local_gateway_control_enabled",
    "scan_interval_seconds",
}
REQUIRED_OPTION_STATUS_TOKENS = {
    "CONF_ANALYTICS_RETENTION_DAYS",
    "CONF_ANALYTICS_RUNTIME",
    "CONF_DEVICE_IMPORT_FILTER",
    "normalize_entry_options",
    "option_status_diagnostics",
}
REQUIRED_DIAGNOSTIC_PAYLOAD_REDACTION_TOKENS = {
    "CONF_SCAN_LOGIN_DEVICE": "scan-login device identifier constant",
    "TO_REDACT": "diagnostics redaction set",
}


def verify_diagnostics_capabilities(config_dir: Path, report: VerificationReport) -> None:
    """Verify installed diagnostics capability flags keep release boundaries."""
    install_root = config_dir / "custom_components" / DOMAIN
    capability_flags = literal_client_capability_flags(install_root)
    if capability_flags is None:
        report.fail("installed diagnostics.py must expose literal client capability flags")
        return

    missing_enabled = [
        key
        for key in DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES
        if capability_flags.get(key) is not True
    ]
    enabled_live = [
        key
        for key in DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES
        if capability_flags.get(key) is not False
    ]
    forbidden = [
        key for key in DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES if key in capability_flags
    ]
    if missing_enabled:
        report.fail(f"installed diagnostics capability flags not true: {missing_enabled}")
    if enabled_live:
        report.fail(f"installed live capability flags not false: {enabled_live}")
    if forbidden:
        report.fail(f"installed forbidden diagnostics capability flags present: {forbidden}")
    if not missing_enabled and not enabled_live and not forbidden:
        report.fact(
            "diagnostics capability flags: "
            f"{len(DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES)} contract true, "
            f"{len(DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES)} live false"
        )
    report.metric(
        "diagnostics_capabilities",
        {
            "contract_true": len(DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES)
            - len(missing_enabled),
            "live_false": len(DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES)
            - len(enabled_live),
            "forbidden_present": len(forbidden),
        },
    )
    _verify_option_status_contract(install_root, report)
    _verify_diagnostic_payload_redaction_contract(install_root, report)
    verify_websocket_event_runtime_contract(install_root, report)


def _verify_option_status_contract(
    install_root: Path,
    report: VerificationReport,
) -> None:
    """Verify installed option_status diagnostics keep runtime option fields."""
    path = install_root / "diagnostic_options.py"
    if not path.exists():
        report.fail("installed diagnostic_options.py is missing")
        return

    content = path.read_text(encoding="utf-8")
    missing_tokens = [
        token for token in REQUIRED_OPTION_STATUS_TOKENS if token not in content
    ]
    fields = _literal_option_status_fields(path)
    missing_fields = sorted(REQUIRED_OPTION_STATUS_FIELDS - fields)
    if missing_tokens:
        report.fail(f"installed option_status diagnostics missing tokens: {missing_tokens}")
    if missing_fields:
        report.fail(f"installed option_status diagnostics missing fields: {missing_fields}")
    if not missing_tokens and not missing_fields:
        report.fact(
            "diagnostics option_status fields: "
            f"{sorted(REQUIRED_OPTION_STATUS_FIELDS)}"
        )
    report.metric(
        "diagnostics_option_status",
        {
            "required_fields": len(REQUIRED_OPTION_STATUS_FIELDS),
            "present_fields": len(REQUIRED_OPTION_STATUS_FIELDS) - len(missing_fields),
            "missing_tokens": len(missing_tokens),
        },
    )


def _literal_option_status_fields(path: Path) -> set[str]:
    """Return literal keys from option_status_diagnostics return dictionaries."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    fields: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "option_status_diagnostics":
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                fields.update(_literal_string_keys(child.value))
    return fields


def _literal_string_keys(node: ast.Dict) -> set[str]:
    """Return literal string keys from an AST dict expression."""
    return {
        key.value
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def _verify_diagnostic_payload_redaction_contract(
    install_root: Path,
    report: VerificationReport,
) -> None:
    """Verify installed diagnostics redact the scan-login device identifier."""
    path = install_root / "diagnostic_payloads.py"
    if not path.exists():
        report.fail("installed diagnostic_payloads.py is missing")
        return

    content = path.read_text(encoding="utf-8")
    missing_tokens = [
        token
        for token in REQUIRED_DIAGNOSTIC_PAYLOAD_REDACTION_TOKENS
        if token not in content
    ]
    if missing_tokens:
        report.fail(
            "installed diagnostic payload redaction missing tokens: "
            f"{missing_tokens}"
        )

    redacted_names = _literal_redaction_names(path)
    if "CONF_SCAN_LOGIN_DEVICE" not in redacted_names:
        report.fail(
            "installed diagnostic payload redaction must include "
            "CONF_SCAN_LOGIN_DEVICE in TO_REDACT"
        )

    missing_count = len(missing_tokens) + int(
        "CONF_SCAN_LOGIN_DEVICE" not in redacted_names
    )
    if missing_count == 0:
        report.fact("diagnostics payload redacts scan-login device identifier")
    report.metric(
        "diagnostics_payload_redaction",
        {
            "required_tokens": len(REQUIRED_DIAGNOSTIC_PAYLOAD_REDACTION_TOKENS),
            "missing_tokens": len(missing_tokens),
            "scan_login_device_redacted": int(
                "CONF_SCAN_LOGIN_DEVICE" in redacted_names
            ),
        },
    )


def _literal_redaction_names(path: Path) -> set[str]:
    """Return variable names included in the installed TO_REDACT set."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "TO_REDACT"
            for target in node.targets
        ):
            continue
        return _name_references(node.value)
    return set()


def _name_references(node: ast.AST) -> set[str]:
    """Return variable names referenced inside an AST expression."""
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}

