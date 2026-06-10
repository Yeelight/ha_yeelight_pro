#!/usr/bin/env python3
"""Run local HA recovery/log validation for Yeelight Pro."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.local_ha_verification.cli import main as verify_local_ha_main  # noqa: E402

DEFAULT_RECOVERY_REPEAT = "2"
DEFAULT_RECOVERY_LOG_TAIL = "2000"


def build_recovery_argv(argv: list[str] | None = None) -> list[str]:
    """Return verifier argv for in-container recovery and log validation."""
    args = list(argv or [])
    if "--skip-docker" in args:
        raise ValueError("recovery verification requires Docker log access")
    if "--repeat" not in args:
        args.extend(["--repeat", DEFAULT_RECOVERY_REPEAT])
    if "--log-tail" not in args:
        args.extend(["--log-tail", DEFAULT_RECOVERY_LOG_TAIL])
    return args


def main(argv: list[str] | None = None) -> int:
    """Run the shared local HA verifier with recovery defaults."""
    try:
        recovery_argv = build_recovery_argv(argv)
    except ValueError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    return verify_local_ha_main(recovery_argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
