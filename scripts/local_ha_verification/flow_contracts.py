"""Config and options flow contract verification."""

from __future__ import annotations

import ast
from pathlib import Path

from .report import VerificationReport

REQUIRED_OPTIONS_FLOW_TOKENS = {
    "merge_options": "visible options are merged without dropping advanced keys",
    "entry_options": "current options are normalized before use",
    "normalize_entry_options": "confirmation compares normalized options",
    "options_require_reload": "reload-sensitive options stay explicit",
    "visible_option_change_count": "confirmation reports visible changes only",
    "options_confirm_schema": "runtime/reload confirmation steps use explicit schema",
    "async_step_confirm_runtime": "runtime-only confirmation step exists",
    "async_step_confirm_reload": "reload-required confirmation step exists",
}
REQUIRED_OPTIONS_FLOW_STEPS = {"init", "confirm_runtime", "confirm_reload"}


def verify_flow_contracts(install_root: Path, report: VerificationReport) -> None:
    """Verify config flow and options flow keep the runtime-options contract."""
    failure_count = len(report.failures)
    options_path = install_root / "options_flow.py"
    config_flow_path = install_root / "config_flow.py"
    if not options_path.exists():
        report.fail("installed options_flow.py is missing")
        return
    if not config_flow_path.exists():
        report.fail("installed config_flow.py is missing")
        return

    options_tree = ast.parse(options_path.read_text(encoding="utf-8"))
    config_flow_tree = ast.parse(config_flow_path.read_text(encoding="utf-8"))
    _verify_options_flow(options_tree, report)
    _verify_config_flow(config_flow_tree, report)
    if len(report.failures) == failure_count:
        report.fact(
            "flow contracts: options flow merge/reload confirmations and "
            "config flow factory present"
        )
    report.metric(
        "flow_contracts",
        {
            "options_flow_steps": sorted(_literal_step_ids(options_tree)),
            "options_flow_tokens": sorted(_called_names(options_tree)),
            "options_factory": _returns_options_flow(config_flow_tree),
        },
    )


def _verify_options_flow(tree: ast.Module, report: VerificationReport) -> None:
    """Verify options_flow.py keeps required calls and step ids."""
    source_calls = _called_names(tree)
    for token, reason in sorted(REQUIRED_OPTIONS_FLOW_TOKENS.items()):
        if token not in source_calls:
            report.fail(f"options flow missing {reason}: {token}")

    steps = _literal_step_ids(tree)
    missing_steps = sorted(REQUIRED_OPTIONS_FLOW_STEPS - steps)
    if missing_steps:
        report.fail(f"options flow missing step ids: {missing_steps}")

    if not _create_entry_uses_pending_options(tree):
        report.fail("options flow create entry does not save pending options")


def _verify_config_flow(tree: ast.Module, report: VerificationReport) -> None:
    """Verify config_flow.py still exposes the options-flow factory."""
    if not _returns_options_flow(tree):
        report.fail("config flow does not return YeelightProOptionsFlow")


def _called_names(tree: ast.Module) -> set[str]:
    """Return function names called by a Python module."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _function_name(node.func)
        if name is not None:
            names.add(name)
    return names


def _literal_step_ids(tree: ast.Module) -> set[str]:
    """Return literal step_id values from show-form or helper calls."""
    steps: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "step_id" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    steps.add(keyword.value.value)
    return steps


def _create_entry_uses_pending_options(tree: ast.Module) -> bool:
    """Return true when async_create_entry saves self._pending_options."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _function_name(node.func) != "async_create_entry":
            continue
        for keyword in node.keywords:
            if keyword.arg != "data":
                continue
            if (
                isinstance(keyword.value, ast.Attribute)
                and keyword.value.attr == "_pending_options"
                and isinstance(keyword.value.value, ast.Name)
                and keyword.value.value.id == "self"
            ):
                return True
    return False


def _returns_options_flow(tree: ast.Module) -> bool:
    """Return true when config_flow returns YeelightProOptionsFlow(config_entry)."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        if _function_name(value.func) != "YeelightProOptionsFlow":
            continue
        if _first_arg_name(value) == "config_entry":
            return True
    return False


def _first_arg_name(node: ast.Call) -> str | None:
    """Return the first positional argument name for a call."""
    if not node.args:
        return None
    first = node.args[0]
    return first.id if isinstance(first, ast.Name) else None


def _function_name(node: ast.expr) -> str | None:
    """Return the called function or method name."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None
