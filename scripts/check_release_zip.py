#!/usr/bin/env python3
"""Validate the Yeelight Pro HACS release zip structure."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = ROOT / "custom_components" / "yeelight_pro"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hacs_preflight_release_file_groups import RELEASE_COMPONENT_FILES  # noqa: E402

REQUIRED_FILES = set(RELEASE_COMPONENT_FILES)

FORBIDDEN_PARTS = {
    "__pycache__",
    ".pytest_cache",
    "cache",
    "generated",
    "htmlcov",
    "tests",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
}
FORBIDDEN_NAMES = {
    ".coverage",
    "coverage.xml",
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


def _iter_release_files() -> list[Path]:
    """Return component files that should be included in the release zip."""
    files: list[Path] = []
    for path in COMPONENT_ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if path.is_dir():
            continue
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            continue
        if path.suffix in FORBIDDEN_SUFFIXES or path.name in FORBIDDEN_NAMES:
            continue
        files.append(path)
    return sorted(files)


def _validate_names(names: set[str]) -> list[str]:
    """Validate release zip file names."""
    errors: list[str] = []
    missing = REQUIRED_FILES - names
    if missing:
        errors.extend(f"missing required file: {name}" for name in sorted(missing))

    for name in sorted(names):
        path = Path(name)
        if name.endswith("/"):
            errors.append(f"directory entry is not allowed: {name}")
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"unsafe zip path: {name}")
        if not name.startswith("custom_components/yeelight_pro/"):
            errors.append(f"unexpected root path: {name}")
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            errors.append(f"forbidden generated/test path: {name}")
        if path.suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden generated file: {name}")
        if path.name in FORBIDDEN_NAMES:
            errors.append(f"forbidden release file: {name}")
    return errors


def _write_zip(path: Path) -> set[str]:
    """Create a release zip and return contained file names."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in _iter_release_files():
            arcname = file_path.relative_to(ROOT).as_posix()
            archive.write(file_path, arcname)
    return _read_zip(path)


def _read_zip(path: Path) -> set[str]:
    """Read an existing release zip."""
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, help="Create and validate this zip path")
    parser.add_argument("--zip", type=Path, help="Validate an existing zip path")
    args = parser.parse_args()

    if args.write and args.zip:
        parser.error("--write and --zip are mutually exclusive")

    if args.write:
        names = _write_zip(args.write)
    elif args.zip:
        names = _read_zip(args.zip)
    else:
        names = {path.relative_to(ROOT).as_posix() for path in _iter_release_files()}

    errors = _validate_names(names)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Release structure OK ({len(names)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
