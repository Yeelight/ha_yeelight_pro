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
    return parser


def sync_runtime_files(config_dir: Path) -> tuple[int, Path]:
    """Copy source runtime files into a local HA config directory."""
    install_root = config_dir / "custom_components" / DOMAIN
    install_root.mkdir(parents=True, exist_ok=True)

    count = 0
    for source_path in _iter_runtime_files(SOURCE_COMPONENT_ROOT):
        relative_path = source_path.relative_to(SOURCE_COMPONENT_ROOT)
        target_path = install_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        count += 1
    return count, install_root


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


def _default_config_dir() -> Path:
    """Return the local HA config dir used by this workspace."""
    candidate = ROOT.parents[3] / "config" / "homeassistant-verify"
    return candidate if candidate.exists() else Path.cwd()


def main() -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args()
    config_dir = args.config_dir.expanduser().resolve()
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


if __name__ == "__main__":
    raise SystemExit(main())
