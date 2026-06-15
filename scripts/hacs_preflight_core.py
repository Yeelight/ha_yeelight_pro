"""Core release-facing preflight checks for Yeelight Pro."""

from __future__ import annotations

import ast
import fnmatch
import importlib
import json
from pathlib import Path
import re
import sys
import types
from typing import Any, Callable

from scripts.hacs_preflight_claims import STALE_DOC_CLAIMS, STALE_DOC_PATTERNS
from scripts.hacs_preflight_data import (
    HACS_PUBLISH_REQUIRED_CHECKS,
    JSON_FILES,
    RELEASE_QUALITY_GATE_TOKENS,
    REQUIRED_HACS_FIELDS,
    REQUIRED_MANIFEST_FIELDS,
    REQUIRED_RELEASE_FILES,
)

MAX_PYTHON_FILE_LINES = 400
FORBIDDEN_RUNTIME_PLATFORM_FILES = {
    "analytics.py",
    "device_tracker.py",
    "humidifier.py",
    "lock.py",
    "media_player.py",
    "notify.py",
    "scene.py",
    "text.py",
    "vacuum.py",
    "water_heater.py",
}
SEMANTIC_VERSION_RE = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?$"
)
USER_VISIBLE_ERROR_CLASSES = {"HomeAssistantError", "ServiceValidationError"}


def check_exists(root: Path) -> list[str]:
    """Check required release-facing files."""
    errors: list[str] = []
    ignore_rules = _gitignore_rules(root)
    for relative_path in sorted(REQUIRED_RELEASE_FILES):
        if not (root / relative_path).exists():
            errors.append(f"missing required file: {relative_path}")
        elif _is_ignored_by_gitignore(relative_path, ignore_rules):
            errors.append(f"required release file is git-ignored: {relative_path}")
    return errors


def _gitignore_rules(root: Path) -> list[tuple[str, bool]]:
    """Return simple .gitignore rules in order."""
    path = root / ".gitignore"
    if not path.exists():
        return []
    rules: list[tuple[str, bool]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        pattern = line[1:] if negated else line
        if pattern:
            rules.append((pattern, negated))
    return rules


def _is_ignored_by_gitignore(
    relative_path: str,
    rules: list[tuple[str, bool]],
) -> bool:
    """Evaluate the simple .gitignore patterns used by this repository."""
    ignored = False
    path = relative_path.replace("\\", "/")
    for pattern, negated in rules:
        normalized = pattern.strip("/").replace("\\", "/")
        if not normalized:
            continue
        if "*" in normalized:
            matches = fnmatch.fnmatch(path, normalized)
        else:
            matches = (
                path == normalized
                or path.startswith(f"{normalized}/")
                or path.endswith(f"/{normalized}")
            )
        if matches:
            ignored = not negated
    return ignored


def check_json(root: Path) -> list[str]:
    """Validate JSON syntax and required metadata fields."""
    errors: list[str] = []
    for relative_path in sorted(JSON_FILES):
        try:
            _read_json(root, relative_path)
        except Exception as err:
            errors.append(f"invalid JSON in {relative_path}: {err}")

    if errors:
        return errors

    manifest = _read_json(root, "custom_components/yeelight_pro/manifest.json")
    missing_manifest = REQUIRED_MANIFEST_FIELDS - set(manifest)
    if missing_manifest:
        errors.append(
            "manifest.json missing fields: " + ", ".join(sorted(missing_manifest))
        )
    if manifest.get("domain") != "yeelight_pro":
        errors.append("manifest.json domain must be yeelight_pro")
    if manifest.get("iot_class") != "cloud_polling":
        errors.append("manifest.json iot_class must match the current polling model")
    manifest_version = manifest.get("version")
    if not isinstance(manifest_version, str) or not SEMANTIC_VERSION_RE.fullmatch(
        manifest_version
    ):
        errors.append("manifest.json version must use semantic versioning")

    hacs = _read_json(root, "hacs.json")
    missing_hacs = REQUIRED_HACS_FIELDS - set(hacs)
    if missing_hacs:
        errors.append("hacs.json missing fields: " + ", ".join(sorted(missing_hacs)))
    if hacs.get("zip_release") is not True:
        errors.append("hacs.json zip_release must be true")
    if hacs.get("filename") != "yeelight_pro.zip":
        errors.append("hacs.json filename must be yeelight_pro.zip")
    return errors


def check_platform_constants(component_root: Path) -> list[str]:
    """Check release platform claims against const.py."""
    errors: list[str] = []
    const_path = component_root / "const.py"
    platforms = _literal_value(const_path, "PLATFORMS")
    if not isinstance(platforms, list):
        errors.append("PLATFORMS must be a literal list")
        return errors

    if "text" in platforms:
        errors.append("text must not be advertised as an enabled platform")
    if "vacuum" in platforms:
        errors.append("vacuum must not be advertised without documented support")
    if "lock" in platforms:
        errors.append("lock must not be advertised without documented door-lock support")
    if len(platforms) != 11:
        errors.append(
            f"default enabled platform count changed: {len(platforms)}"
        )
    forbidden_platforms = {
        Path(platform).stem
        for platform in FORBIDDEN_RUNTIME_PLATFORM_FILES
        if Path(platform).stem in platforms
    }
    if forbidden_platforms:
        errors.append(
            "unsupported runtime platforms are enabled: "
            f"{sorted(forbidden_platforms)}"
        )
    errors.extend(check_forbidden_runtime_platform_files(component_root))
    return errors


def check_forbidden_runtime_platform_files(component_root: Path) -> list[str]:
    """Reject runtime platform files that Yeelight APIs do not back."""
    errors: list[str] = []
    for forbidden_name in sorted(FORBIDDEN_RUNTIME_PLATFORM_FILES):
        path = component_root / forbidden_name
        if path.exists():
            errors.append(
                f"unsupported runtime platform file must be removed: {forbidden_name}"
            )
    projector_root = component_root / "projector"
    if projector_root.exists():
        for forbidden_name in sorted(FORBIDDEN_RUNTIME_PLATFORM_FILES):
            path = projector_root / forbidden_name
            if path.exists():
                errors.append(
                    "unsupported projector platform file must be removed: "
                    f"projector/{forbidden_name}"
                )
    return errors


def check_python_file_line_counts(root: Path) -> list[str]:
    """Keep source files inside the project line-count boundary."""
    errors: list[str] = []
    for path in _iter_line_count_python_files(root):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_PYTHON_FILE_LINES:
            relative_path = path.relative_to(root)
            errors.append(
                f"{relative_path} exceeds {MAX_PYTHON_FILE_LINES} lines: "
                f"{line_count}"
            )
    return errors


def _iter_line_count_python_files(root: Path) -> list[Path]:
    """Return project Python files covered by the line-count gate."""
    paths = list((root / "custom_components" / "yeelight_pro").rglob("*.py"))
    paths.extend((root / "scripts").rglob("*.py"))
    paths.extend(root.glob("*.py"))
    return sorted(path for path in paths if "__pycache__" not in path.parts)


def check_release_quality_gates(root: Path) -> list[str]:
    """Ensure local and CI release gates keep lint and type-check coverage."""
    errors: list[str] = []
    for relative_path, required_tokens in RELEASE_QUALITY_GATE_TOKENS.items():
        path = root / relative_path
        if not path.exists():
            errors.append(f"release quality gate requires {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"{relative_path} missing {reason}: {token}")
    errors.extend(_check_hacs_publish_commands(root / "hacs_publish.py"))
    return errors


def check_user_visible_error_redaction(component_root: Path) -> list[str]:
    """Reject HA user-facing errors that interpolate raw runtime values."""
    errors: list[str] = []
    for path in sorted(component_root.rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "__init__.py":
            continue
        if path.name == "entity_errors.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node.func) not in USER_VISIBLE_ERROR_CLASSES:
                continue
            if node.args and _contains_dynamic_string(node.args[0]):
                errors.append(
                    f"{path.relative_to(component_root.parent.parent)}:"
                    f"{node.lineno} uses dynamic user-visible HA error text"
                )
    return errors


def check_iot_registry_integrity(component_root: Path) -> list[str]:
    """Check static Yeelight IoT registry invariants."""
    iot_registry, validate_iot_registry = _load_iot_registry_contract(component_root)

    return validate_iot_registry(iot_registry())


def check_readme_claims(root: Path) -> list[str]:
    """Block stale release claims in current release-facing docs."""
    errors: list[str] = []
    doc_paths = _release_claim_doc_paths(root)
    for path in doc_paths:
        content = path.read_text(encoding="utf-8")
        for claim in STALE_DOC_CLAIMS:
            if claim in content:
                errors.append(
                    f"stale release claim in {_release_claim_label(path, root)}: {claim}"
                )
        for pattern in STALE_DOC_PATTERNS:
            if re.search(pattern, content, flags=re.IGNORECASE):
                errors.append(
                    "stale release claim in "
                    f"{_release_claim_label(path, root)}: /{pattern}/"
                )
    return errors


def _release_claim_doc_paths(root: Path) -> list[Path]:
    """Return release-facing docs that must not drift from runtime facts."""
    paths = [
        root / "README.md",
        root / "README_zh.md",
        root / "CHANGELOG.md",
        root / "RELEASE_GUIDE.md",
        *sorted((root / "docs").glob("*.md")),
    ]
    homeassistant_progress = root.parent.parent / "最新进度.md"
    if homeassistant_progress.exists():
        paths.append(homeassistant_progress)
    return paths


def _release_claim_label(path: Path, root: Path) -> str:
    """Return a stable path label for claim-guard errors."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path.relative_to(root.parent.parent))


def _read_json(root: Path, relative_path: str) -> dict:
    """Read a JSON file relative to the repository root."""
    with (root / relative_path).open(encoding="utf-8") as file:
        return json.load(file)


def _literal_value(module_path: Path, variable_name: str) -> object | None:
    """Read a simple constant from a Python module without importing HA modules."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    try:
                        return ast.literal_eval(node.value)
                    except (TypeError, ValueError):
                        return None
    return None


def _call_name(func: ast.expr) -> str | None:
    """Return a simple call name from Name or Attribute nodes."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _contains_dynamic_string(node: ast.AST) -> bool:
    """Return true for f-string or string concatenation expressions."""
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_string_expr(node.left) or _is_string_expr(node.right)
    return False


def _is_string_expr(node: ast.AST) -> bool:
    """Return true for expressions participating in string construction."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_string_expr(node.left) or _is_string_expr(node.right)
    return False


def _check_hacs_publish_commands(path: Path) -> list[str]:
    """Validate release script commands without depending on list formatting."""
    errors: list[str] = []
    if not path.exists():
        return ["release quality gate requires hacs_publish.py"]

    checks = _literal_value(path, "CHECKS")
    if not isinstance(checks, list):
        return ["hacs_publish.py must define literal CHECKS"]

    commands = {
        tuple(command)
        for command in checks
        if isinstance(command, list)
        and all(isinstance(part, str) for part in command)
    }
    for name, expected in HACS_PUBLISH_REQUIRED_CHECKS.items():
        if expected not in commands:
            errors.append(
                "hacs_publish.py missing local release "
                f"{name} command: {' '.join(expected)}"
            )
    return errors


def _load_iot_registry_contract(
    component_root: Path,
) -> tuple[Callable[[], Any], Callable[[Any], list[str]]]:
    """Load capability modules without importing the HA integration runtime."""
    package_name = f"_yeelight_preflight_{abs(hash(str(component_root)))}"
    root_package = types.ModuleType(package_name)
    root_package.__path__ = [str(component_root)]  # type: ignore[attr-defined]
    root_package.__package__ = package_name
    sys.modules[package_name] = root_package

    capabilities_name = f"{package_name}.capabilities"
    capabilities_package = types.ModuleType(capabilities_name)
    capabilities_package.__path__ = [str(component_root / "capabilities")]  # type: ignore[attr-defined]
    capabilities_package.__package__ = capabilities_name
    sys.modules[capabilities_name] = capabilities_package

    registry_module = importlib.import_module(f"{capabilities_name}.registry")
    validation_module = importlib.import_module(f"{capabilities_name}.validation")
    return registry_module.iot_registry, validation_module.validate_iot_registry
