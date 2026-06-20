#!/usr/bin/env python3
"""Summarize a private-house coverage audit JSON into actionable conclusions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.private_house_audit.classification import (  # noqa: E402
    classify_report,
    markdown_report,
)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Summarize Yeelight Pro private-house coverage audit JSON."
    )
    parser.add_argument("report", type=Path, help="Path to audit JSON report.")
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--markdown-output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    source = _load_json(args.report)
    classified = classify_report(source)
    markdown = markdown_report(classified)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(classified, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("coverage report must be a JSON object")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
