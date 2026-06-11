"""Runtime entity-count verification from Home Assistant logs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
import re

from .report import VerificationReport

ADDED_ENTITIES_RE = re.compile(r"Added\s+(\d+)\s+([a-z_ ]+?)\s+entities\b")
ZH_ADDED_ENTITIES_RE = re.compile(r"已添加\s+(\d+)\s+个\s+([a-z_]+)\s+实体\b")
RECONCILED_ACTIVE_RE = re.compile(
    r"Reconciled Yeelight Pro entity registry\b.*?\bactive=(\d+)\b"
)


def verify_runtime_entity_counts(
    lines: Iterable[str],
    report: VerificationReport,
    *,
    expected_entity_counts: Mapping[str, int],
) -> None:
    """Verify active entities from runtime add/reconcile logs."""
    line_list = list(lines)
    expected_counts = Counter(expected_entity_counts)
    counts = runtime_entity_counts(line_list)
    active_total = latest_reconciled_active_count(line_list)
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
    elif active_total != entity_total:
        report.fail(
            "runtime active entity total mismatch: "
            f"reconciled active={active_total}, added domains total={entity_total}"
        )
    else:
        report.fact(f"runtime active entities: {active_total}")
    report.metric("runtime_entities", entity_total)
    report.metric("runtime_entity_domains", dict(sorted(counts.items())))


def runtime_entity_counts(lines: Iterable[str]) -> Counter[str]:
    """Return active entity counts from the latest platform add log for each domain."""
    counts: Counter[str] = Counter()
    for line in lines:
        match = ADDED_ENTITIES_RE.search(line) or ZH_ADDED_ENTITIES_RE.search(line)
        if match is None:
            continue
        count, domain = match.groups()
        counts[_normalize_domain(domain)] = int(count)
    return counts


def latest_reconciled_active_count(lines: Iterable[str]) -> int | None:
    """Return the latest entity-registry reconcile active count."""
    active: int | None = None
    for line in lines:
        match = RECONCILED_ACTIVE_RE.search(line)
        if match is not None:
            active = int(match.group(1))
    return active


def _normalize_domain(value: str) -> str:
    """Normalize HA platform names as they appear in logs."""
    return value.strip().replace(" ", "_")
