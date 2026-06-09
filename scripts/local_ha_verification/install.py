"""Installed component verification."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .constants import (
    DOMAIN,
    EXCLUDED_COMPARE_PARTS,
    EXCLUDED_COMPARE_SUFFIXES,
    FORBIDDEN_INSTALL_NAMES,
    FORBIDDEN_INSTALL_PARTS,
    REQUIRED_RUNTIME_MODULES,
    SOURCE_COMPONENT_ROOT,
)
from .report import VerificationReport


@dataclass(frozen=True)
class RuntimeDiff:
    """Runtime source/install comparison result."""

    missing: tuple[str, ...]
    extra: tuple[str, ...]
    changed: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Return true when runtime source and installed files match."""
        return not self.missing and not self.extra and not self.changed


def runtime_diff(source_root: Path, install_root: Path) -> RuntimeDiff:
    """Compare runtime files between source and an installed HA component."""
    source = _runtime_files(source_root)
    installed = _runtime_files(install_root)
    missing = tuple(sorted(set(source) - set(installed)))
    extra = tuple(sorted(set(installed) - set(source)))
    changed = tuple(
        sorted(
            path
            for path in set(source) & set(installed)
            if source[path] != installed[path]
        )
    )
    return RuntimeDiff(missing=missing, extra=extra, changed=changed)


def forbidden_install_paths(install_root: Path) -> list[str]:
    """Return forbidden non-runtime files present in the installed component."""
    found: list[str] = []
    if not install_root.exists():
        return found
    for path in install_root.rglob("*"):
        rel = path.relative_to(install_root)
        if any(part in FORBIDDEN_INSTALL_PARTS for part in rel.parts):
            found.append(rel.as_posix())
            continue
        if path.name in FORBIDDEN_INSTALL_NAMES:
            found.append(rel.as_posix())
    return sorted(set(found))


def cache_artifact_count(install_root: Path) -> int:
    """Count HA-generated Python cache artifacts in the install directory."""
    if not install_root.exists():
        return 0
    return sum(
        1
        for path in install_root.rglob("*")
        if "__pycache__" in path.parts or path.suffix == ".pyc"
    )


def verify_installation(
    config_dir: Path,
    report: VerificationReport,
    *,
    source_root: Path = SOURCE_COMPONENT_ROOT,
) -> None:
    """Verify installed component shape and source sync."""
    install_root = config_dir / "custom_components" / DOMAIN
    if not install_root.exists():
        report.fail(f"installed component missing: {install_root}")
        return

    diff = runtime_diff(source_root, install_root)
    if diff.ok:
        report.fact("installed runtime files match source")
    else:
        if diff.missing:
            report.fail(f"installed component missing files: {list(diff.missing[:10])}")
        if diff.extra:
            report.fail(f"installed component has extra files: {list(diff.extra[:10])}")
        if diff.changed:
            report.fail(f"installed component has changed files: {list(diff.changed[:10])}")

    forbidden = forbidden_install_paths(install_root)
    if forbidden:
        report.fail(f"forbidden install files present: {forbidden[:10]}")
    else:
        report.fact("no tests/text.py/coverage caches in install target")

    cache_count = cache_artifact_count(install_root)
    if cache_count:
        report.warn(f"HA-generated Python cache artifacts present: {cache_count}")

    verify_required_modules(install_root, report)


def verify_required_modules(
    install_root: Path,
    report: VerificationReport,
    *,
    modules: tuple[str, ...] = REQUIRED_RUNTIME_MODULES,
) -> None:
    """Verify key runtime module files are present in the installed component."""
    missing = [
        module
        for module in modules
        if not _module_file(install_root, module).exists()
    ]
    if missing:
        report.fail(f"installed support modules missing: {missing}")
        return
    module_names = [module.rsplit(".", 1)[-1] for module in modules]
    report.fact("installed support modules present: " + ", ".join(module_names))


def _module_file(install_root: Path, module: str) -> Path:
    """Map a Yeelight Pro module name to its installed Python file."""
    prefix = f"custom_components.{DOMAIN}."
    relative = module.removeprefix(prefix).replace(".", "/")
    return install_root / f"{relative}.py"


def _runtime_files(root: Path) -> dict[str, str]:
    """Return runtime files under a component root as relative path -> digest."""
    files: dict[str, str] = {}
    if not root.exists():
        return files
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_COMPARE_PARTS for part in rel.parts):
            continue
        if path.suffix in EXCLUDED_COMPARE_SUFFIXES:
            continue
        files[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files
