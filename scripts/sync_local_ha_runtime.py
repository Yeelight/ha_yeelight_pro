#!/usr/bin/env python3
"""Sync Yeelight Pro runtime files into the local HA verification config."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.local_ha_verification.constants import (  # noqa: E402
    DOMAIN,
    EXCLUDED_COMPARE_PARTS,
    EXCLUDED_COMPARE_SUFFIXES,
    FORBIDDEN_INSTALL_NAMES,
    SOURCE_COMPONENT_ROOT,
)
from scripts.local_ha_verification.install import forbidden_install_paths  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=_default_config_dir(),
        help="Home Assistant config directory used for local verification.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned runtime sync changes without modifying files.",
    )
    return parser


def sync_runtime_files(config_dir: Path) -> tuple[int, Path]:
    """Copy source runtime files into a local HA config directory."""
    install_root = config_dir / "custom_components" / DOMAIN
    install_root.mkdir(parents=True, exist_ok=True)

    source_files = _iter_runtime_files(SOURCE_COMPONENT_ROOT)
    expected_files = {
        path.relative_to(SOURCE_COMPONENT_ROOT).as_posix()
        for path in source_files
    }
    _remove_stale_runtime_files(install_root, expected_files)
    _remove_generated_runtime_caches(install_root)

    count = 0
    for source_path in source_files:
        relative_path = source_path.relative_to(SOURCE_COMPONENT_ROOT)
        target_path = install_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        count += 1
    return count, install_root


def planned_runtime_sync(config_dir: Path) -> dict[str, object]:
    """Return a non-mutating summary of the runtime sync plan."""
    install_root = config_dir / "custom_components" / DOMAIN
    source_files = _iter_runtime_files(SOURCE_COMPONENT_ROOT)
    expected_files = {
        path.relative_to(SOURCE_COMPONENT_ROOT).as_posix()
        for path in source_files
    }
    installed_files = _iter_install_runtime_files(install_root)
    stale_files = sorted(
        path
        for path in installed_files
        if path not in expected_files
    )
    changed_files: list[str] = []
    for source_path in source_files:
        relative = source_path.relative_to(SOURCE_COMPONENT_ROOT).as_posix()
        if _install_file_differs(source_path, install_root, relative):
            changed_files.append(relative)
    return {
        "install_root": install_root,
        "source_file_count": len(source_files),
        "stale_files": stale_files,
        "changed_or_missing_files": sorted(changed_files),
        "cache_artifact_count": _generated_runtime_cache_count(install_root),
    }


def _iter_runtime_files(source_root: Path) -> list[Path]:
    """Return source files that belong in an installed runtime component."""
    files: list[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(source_root)
        if any(part in EXCLUDED_COMPARE_PARTS for part in relative_path.parts):
            continue
        if path.suffix in EXCLUDED_COMPARE_SUFFIXES:
            continue
        if path.name in FORBIDDEN_INSTALL_NAMES:
            continue
        files.append(path)
    return sorted(files)


def _remove_stale_runtime_files(
    install_root: Path,
    expected_files: set[str],
) -> None:
    """Remove installed runtime files that no longer exist in source."""
    for path in sorted(install_root.rglob("*"), reverse=True):
        if not path.is_file():
            continue
        relative_path = path.relative_to(install_root)
        if any(part in EXCLUDED_COMPARE_PARTS for part in relative_path.parts):
            continue
        if path.suffix in EXCLUDED_COMPARE_SUFFIXES:
            continue
        if relative_path.as_posix() not in expected_files:
            path.unlink()
    for path in sorted(install_root.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def _remove_generated_runtime_caches(install_root: Path) -> None:
    """Remove Python caches from the installed runtime mirror."""
    for path in sorted(install_root.rglob("*"), reverse=True):
        if path.is_file() and (
            "__pycache__" in path.parts
            or path.suffix in EXCLUDED_COMPARE_SUFFIXES
        ):
            path.unlink()
    for path in sorted(install_root.rglob("*"), reverse=True):
        if path.is_dir() and path.name == "__pycache__":
            path.rmdir()


def _iter_install_runtime_files(install_root: Path) -> set[str]:
    """Return installed runtime file paths considered by sync cleanup."""
    if not install_root.exists():
        return set()
    files: set[str] = set()
    for path in install_root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(install_root)
        if any(part in EXCLUDED_COMPARE_PARTS for part in relative_path.parts):
            continue
        if path.suffix in EXCLUDED_COMPARE_SUFFIXES:
            continue
        files.add(relative_path.as_posix())
    return files


def _install_file_differs(source_path: Path, install_root: Path, relative: str) -> bool:
    """Return whether an installed file is missing or byte-different."""
    target_path = install_root / relative
    if not target_path.exists():
        return True
    return source_path.read_bytes() != target_path.read_bytes()


def _generated_runtime_cache_count(install_root: Path) -> int:
    """Return generated cache artifact count without deleting anything."""
    if not install_root.exists():
        return 0
    return sum(
        1
        for path in install_root.rglob("*")
        if path.is_file()
        and ("__pycache__" in path.parts or path.suffix in EXCLUDED_COMPARE_SUFFIXES)
    )


def _default_config_dir() -> Path:
    """Return the local HA config dir used by this workspace."""
    candidate = ROOT.parents[3] / "config" / "homeassistant-verify"
    return candidate if candidate.exists() else Path.cwd()


def main() -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args()
    config_dir = args.config_dir.expanduser().resolve()
    if args.dry_run:
        plan = _runtime_sync_plan_for_output(config_dir)
        print(f"Install root: {plan.install_root}")
        print(f"Source runtime files: {plan.source_file_count}")
        print(f"Changed or missing files: {len(plan.changed_or_missing_files)}")
        for path in plan.changed_or_missing_files[:20]:
            print(f"  update {path}")
        print(f"Stale files: {len(plan.stale_files)}")
        for path in plan.stale_files[:20]:
            print(f"  remove {path}")
        print(f"Generated cache artifacts: {plan.cache_artifact_count}")
        return 0
    count, install_root = sync_runtime_files(config_dir)
    print(f"Synced {count} runtime files into {install_root}")
    forbidden = forbidden_install_paths(install_root)
    if forbidden:
        print(
            "ERROR: forbidden local HA install files remain: "
            + ", ".join(forbidden[:10]),
            file=sys.stderr,
        )
        return 1
    return 0


class _RuntimeSyncPlan:
    """Typed view of the dry-run sync plan for CLI output."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.install_root = payload["install_root"]
        self.source_file_count = int(payload["source_file_count"])
        self.stale_files = list(payload["stale_files"])  # type: ignore[arg-type]
        self.changed_or_missing_files = list(
            payload["changed_or_missing_files"]  # type: ignore[arg-type]
        )
        self.cache_artifact_count = int(payload["cache_artifact_count"])


def _runtime_sync_plan_for_output(config_dir: Path) -> _RuntimeSyncPlan:
    """Return a typed dry-run plan for CLI output."""
    return _RuntimeSyncPlan(planned_runtime_sync(config_dir))


if __name__ == "__main__":
    raise SystemExit(main())
