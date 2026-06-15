#!/usr/bin/env python3
"""Print HACS publication instructions after local checks pass."""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHECKS = [
    [
        "python3",
        "-m",
        "compileall",
        "-q",
        "custom_components/yeelight_pro",
        "scripts",
        "hacs_publish.py",
    ],
    ["ruff", "check", "custom_components/yeelight_pro", "scripts", "hacs_publish.py"],
    [
        "mypy",
        "--ignore-missing-imports",
        "--explicit-package-bases",
        "--exclude",
        "custom_components/yeelight_pro/tests",
        "custom_components/yeelight_pro",
        "scripts",
        "hacs_publish.py",
    ],
    ["pytest", "-q"],
    ["python3", "validate_hacs.py"],
    ["python3", "scripts/check_release_zip.py"],
]


def _run_checks() -> bool:
    """Run local release checks."""
    for command in CHECKS:
        print(f"$ {' '.join(command)}", flush=True)
        result = subprocess.run(command, check=False, cwd=ROOT)
        if result.returncode != 0:
            print(f"Check failed: {' '.join(command)}", file=sys.stderr)
            return False
    return True


def build_parser() -> argparse.ArgumentParser:
    """Build the release-check CLI parser."""
    parser = argparse.ArgumentParser(
        description="Run Yeelight Pro local release checks.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Explicitly run local release checks without publishing.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    build_parser().parse_args(argv)

    if not _run_checks():
        return 1

    print(
        """
Local checks passed.

Manual publication steps:

1. Create a reviewed GitHub release with yeelight_pro.zip.
2. Submit the repository to HACS: https://hacs.xyz/docs/publish/start
3. Submit Home Assistant brand assets only after release validation.

Do not publish if README, CHANGELOG, manifest version, or release zip contents
do not match the code that was tested.
""".strip()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
