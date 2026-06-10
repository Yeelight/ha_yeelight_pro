#!/usr/bin/env python3
"""Compatibility entrypoint for local Home Assistant verification."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.verify_local_ha import main as verify_local_ha_main  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Delegate to the canonical local HA verifier."""
    return verify_local_ha_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
