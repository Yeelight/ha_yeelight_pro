"""Runtime entity-count verification from Home Assistant logs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
import re

from .report import VerificationReport

ADDED_ENTITIES_RE = re.compile(r"Added\s+(\d+)\s+([a-z_ ]+?)\s+entities\b")
ZH_ADDED_ENTITIES_RE = re.compile(r"已添加\s+(\d+)\s+个\s+([a-z_]+)\s+实体\b")
RECONCILED_ACTIVE_RE = re.compile(
    r"Reconciled Yeelight Pro entity registry\b.*?\bentry\s+([^:]+):.*?\bactive=(\d+)\b"
)
SETUP_COMPLETE_RE = re.compile(
    r"Yeelight Pro integration setup complete for house\s+(.+?)\s+\(([^)]+)\)"
)
LAN_SETUP_COMPLETE_RE = re.compile(
    r"Yeelight Pro LAN-only setup complete for gateway\s+(.+)$"
)


def verify_runtime_entity_counts(
    lines: Iterable[str],
    report: VerificationReport,
    *,
    expected_entity_counts: Mapping[str, int],
) -> None:
    """Verify active entities from runtime add/reconcile logs."""
    line_list = list(lines)
    runtime_lines = latest_setup_runtime_lines(line_list)
    expected_counts = Counter(expected_entity_counts)
    counts = runtime_entity_counts(runtime_lines)
    active_total = latest_reconciled_active_total(runtime_lines)
    if not counts:
        report.fail("runtime entity add logs not found")
        return

    entity_total = sum(counts.values())
    unexpected_domains = {
        domain: count
        for domain, count in counts.items()
        if count > expected_counts.get(domain, 0)
    }
    if unexpected_domains:
        report.fail(
            "runtime entity domain distribution exceeds retained registry: "
            f"unexpected {dict(sorted(unexpected_domains.items()))}, "
            f"retained {dict(sorted(expected_counts.items()))}"
        )
    else:
        report.fact(f"runtime entity domains: {dict(sorted(counts.items()))}")
        missing_runtime = {
            domain: expected_count - counts.get(domain, 0)
            for domain, expected_count in expected_counts.items()
            if expected_count > counts.get(domain, 0)
        }
        if missing_runtime:
            report.fact(
                "runtime omitted retained registry domains: "
                f"{dict(sorted(missing_runtime.items()))}"
            )
    if active_total is None:
        report.fail("runtime registry reconcile active count not found")
    elif active_total < entity_total:
        report.fail(
            "runtime active entity total mismatch: "
            f"reconciled active={active_total}, added domains total={entity_total}"
        )
    else:
        report.fact(f"runtime active entities: {active_total}")
        if active_total > entity_total:
            report.fact(
                "runtime active registry candidates exceed add logs: "
                f"active={active_total}, added={entity_total}"
            )
    report.metric("runtime_entities", active_total if active_total is not None else entity_total)
    report.metric("runtime_entity_domains", dict(sorted(counts.items())))


def runtime_entity_counts(lines: Iterable[str]) -> Counter[str]:
    """Return active entity counts from the latest complete setup window."""
    counts: Counter[str] = Counter()
    for line in lines:
        match = ADDED_ENTITIES_RE.search(line) or ZH_ADDED_ENTITIES_RE.search(line)
        if match is None:
            continue
        count, domain = match.groups()
        counts[_normalize_domain(domain)] += int(count)
    return counts


def latest_setup_runtime_lines(lines: Iterable[str]) -> list[str]:
    """Return current runtime setup windows for each active connection mode."""
    line_list = list(lines)
    windows = _setup_windows(line_list)
    if not windows:
        return line_list

    latest_by_mode: dict[str, tuple[int, int]] = {}
    for mode, start, end in windows:
        latest_by_mode[mode] = (start, end)

    latest_lines: list[str] = []
    for _mode, start, end in sorted(
        (
            (mode, start, end)
            for mode, (start, end) in latest_by_mode.items()
        ),
        key=lambda item: item[1],
    ):
        latest_lines.extend(line_list[start:end])
    return latest_lines


def _setup_windows(lines: list[str]) -> list[tuple[str, int, int]]:
    """Return setup windows as (mode, start, exclusive_end)."""
    windows: list[tuple[str, int, int]] = []
    start = 0
    for index, line in enumerate(lines):
        mode = _setup_mode(line)
        if mode is None:
            continue
        windows.append((mode, start, index + 1))
        start = index + 1
    return windows


def _setup_mode(line: str) -> str | None:
    """Return the Yeelight Pro connection mode represented by a setup log."""
    if LAN_SETUP_COMPLETE_RE.search(line):
        return "lan"
    match = SETUP_COMPLETE_RE.search(line)
    if match is None:
        return None
    return match.group(2).strip().lower() or "cloud"


def latest_reconciled_active_count(lines: Iterable[str]) -> int | None:
    """Return the latest entity-registry reconcile active count."""
    active: int | None = None
    for line in lines:
        match = RECONCILED_ACTIVE_RE.search(line)
        if match is not None:
            active = int(match.group(2))
    return active


def latest_reconciled_active_total(lines: Iterable[str]) -> int | None:
    """Return the sum of latest active counts per config entry."""
    active_by_entry: dict[str, int] = {}
    for line in lines:
        match = RECONCILED_ACTIVE_RE.search(line)
        if match is None:
            continue
        entry_id, active = match.groups()
        active_by_entry[entry_id.strip()] = int(active)
    if not active_by_entry:
        return None
    return sum(active_by_entry.values())


def _normalize_domain(value: str) -> str:
    """Normalize HA platform names as they appear in logs."""
    return value.strip().replace(" ", "_")
