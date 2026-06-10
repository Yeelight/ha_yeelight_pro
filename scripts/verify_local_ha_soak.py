#!/usr/bin/env python3
"""Run a bounded local HA soak verification for Yeelight Pro."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.local_ha_verification.cli import main as verify_local_ha_main  # noqa: E402

DEFAULT_SOAK_SECONDS = "60"
DEFAULT_SOAK_INTERVAL = "15"


def build_soak_argv(argv: list[str] | None = None) -> list[str]:
    """Return verifier argv with bounded soak defaults unless explicitly provided."""
    args = list(argv or [])
    if "--soak-seconds" not in args:
        args.extend(["--soak-seconds", DEFAULT_SOAK_SECONDS])
    if "--soak-interval" not in args:
        args.extend(["--soak-interval", DEFAULT_SOAK_INTERVAL])
    return args


def main(argv: list[str] | None = None) -> int:
    """Run the shared local HA verifier with soak defaults."""
    return verify_local_ha_main(build_soak_argv(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
