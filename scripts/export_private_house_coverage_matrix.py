#!/usr/bin/env python3
"""Export private-house coverage classification JSON as a CSV matrix."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections.abc import Mapping
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.private_house_audit.classification import classify_report  # noqa: E402
from scripts.private_house_audit.coverage_matrix_rows import (  # noqa: E402
    FIELDNAMES,
    coverage_matrix_row,
)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Export Yeelight Pro private-house classification JSON to CSV."
    )
    parser.add_argument("classification", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    classified = _classified_report(_load_json(args.classification))
    rows = [
        coverage_matrix_row(item)
        for item in _sequence(classified.get("devices"))
    ]
    rows.extend(
        coverage_matrix_row(item)
        for item in _sequence(classified.get("topology_entities"))
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


def _sequence(value: Any) -> list[Any]:
    """Return a list value while excluding strings."""
    return value if isinstance(value, list) else []


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("classification report must be a JSON object")
    return value


def _classified_report(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a classified report, accepting raw audit JSON as input."""
    devices = _sequence(value.get("devices"))
    if devices and all(
        isinstance(item, Mapping) and isinstance(item.get("conclusion"), Mapping)
        for item in devices
    ):
        return dict(value)
    return classify_report(value)


if __name__ == "__main__":
    raise SystemExit(main())
