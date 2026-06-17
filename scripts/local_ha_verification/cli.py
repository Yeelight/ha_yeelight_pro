"""CLI entrypoint for local HA verification."""

from __future__ import annotations

import argparse
from pathlib import Path
import time

from .constants import (
    DEFAULT_CONTAINER,
    DEFAULT_ENTITY_COUNTS,
    DEFAULT_EXPECTED_CONFIG_ENTRIES,
    DEFAULT_EXPECTED_DEVICES,
    DEFAULT_EXPECTED_ENTITIES,
    DEFAULT_HA_URL,
    ROOT,
)
from .diagnostics import verify_diagnostics_capabilities
from .flow_contracts import verify_flow_contracts
from .i18n import verify_i18n_contracts
from .install import verify_installation
from .report import VerificationReport
from .runtime import (
    verify_docker,
    verify_ha_url,
    verify_logs,
    verify_runtime_entities,
    verify_synthetic_log_recovery,
)
from .services import verify_services
from .storage import verify_product_schema_cache, verify_storage
from .storage import expected_runtime_entity_counts

DRIFT_EXCLUDED_METRICS = frozenset({
    "entity_device_links",
    "entity_registry_disabled_by",
    "retained_entities",
    "retained_entity_domains",
})


def parse_domain_counts(value: str) -> dict[str, int]:
    """Parse comma-separated entity-domain counts."""
    result: dict[str, int] = {}
    for item in value.split(","):
        if not item:
            continue
        name, _, raw_count = item.partition("=")
        if not name or not raw_count:
            raise argparse.ArgumentTypeError(
                f"invalid domain count item: {item!r}"
            )
        result[name.strip()] = int(raw_count)
    return result


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", type=Path, default=_default_config_dir())
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--ha-url", default=DEFAULT_HA_URL)
    parser.add_argument("--skip-docker", action="store_true")
    parser.add_argument("--skip-url", action="store_true")
    parser.add_argument("--log-tail", type=int, default=800)
    parser.add_argument("--repeat", type=_positive_int, default=1)
    parser.add_argument("--repeat-delay", type=_non_negative_float, default=0.0)
    parser.add_argument("--soak-seconds", type=_non_negative_float, default=0.0)
    parser.add_argument("--soak-interval", type=_positive_float, default=30.0)
    parser.add_argument(
        "--expected-config-entries",
        type=int,
        default=DEFAULT_EXPECTED_CONFIG_ENTRIES,
    )
    parser.add_argument("--expected-devices", type=int, default=DEFAULT_EXPECTED_DEVICES)
    parser.add_argument(
        "--expected-entities",
        type=int,
        default=DEFAULT_EXPECTED_ENTITIES,
    )
    parser.add_argument(
        "--expected-domain-counts",
        type=parse_domain_counts,
        default=DEFAULT_ENTITY_COUNTS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    started_at = time.monotonic()
    reports = _run_repeated(args)
    if args.soak_seconds:
        reports.extend(_run_soak(args, started_at=started_at))
    _verify_stable_metrics(reports)

    _print_reports(reports)
    if all(report.ok for report in reports):
        suffix = _success_suffix(args, reports)
        print(f"\nLocal HA verification passed{suffix}.")
        return 0
    print("\nLocal HA verification failed.")
    return 1


def _run_repeated(args: argparse.Namespace) -> list[VerificationReport]:
    """Run the requested fixed repeat count."""
    reports: list[VerificationReport] = []

    for index in range(args.repeat):
        if index and args.repeat_delay:
            time.sleep(args.repeat_delay)
        reports.append(_run_once(args))
    return reports


def _run_soak(
    args: argparse.Namespace,
    *,
    started_at: float,
) -> list[VerificationReport]:
    """Run additional samples until the bounded soak window is covered."""
    reports: list[VerificationReport] = []
    deadline = started_at + args.soak_seconds
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        time.sleep(min(args.soak_interval, remaining))
        reports.append(_run_once(args))
    return reports


def _run_once(args: argparse.Namespace) -> VerificationReport:
    """Run one local HA verification pass."""
    report = VerificationReport()
    config_dir = args.config_dir.expanduser().resolve()

    if not config_dir.exists():
        report.fail(f"config directory does not exist: {config_dir}")
    else:
        report.fact(f"config directory exists: {config_dir}")
        verify_installation(config_dir, report)
        verify_storage(
            config_dir,
            report,
            expected_config_entries=args.expected_config_entries,
            expected_devices=args.expected_devices,
            expected_entities=args.expected_entities,
            expected_entity_counts=args.expected_domain_counts,
        )
        verify_services(config_dir, report)
        verify_i18n_contracts(config_dir / "custom_components" / "yeelight_pro", report)
        verify_flow_contracts(config_dir / "custom_components" / "yeelight_pro", report)
        verify_diagnostics_capabilities(config_dir, report)
        verify_product_schema_cache(config_dir, report)

    if not args.skip_docker:
        verify_docker(args.container, report)
        verify_logs(args.container, report, tail=args.log_tail)
        runtime_entity_counts = (
            expected_runtime_entity_counts(config_dir, args.expected_domain_counts)
            if config_dir.exists()
            else args.expected_domain_counts
        )
        verify_runtime_entities(
            args.container,
            report,
            tail=args.log_tail,
            expected_entity_counts=dict(runtime_entity_counts),
        )
    verify_synthetic_log_recovery(report)
    if not args.skip_url:
        verify_ha_url(args.ha_url, report)

    return report


def _print_reports(reports: list[VerificationReport]) -> None:
    """Print one or more local HA verification reports."""
    print("Yeelight Pro local HA verification")
    print("=" * 40)
    for index, report in enumerate(reports, start=1):
        if len(reports) > 1:
            print(f"-- run {index}/{len(reports)} --")
        for fact in report.facts:
            print(f"[OK] {fact}")
        for warning in report.warnings:
            print(f"[WARN] {warning}")
        for failure in report.failures:
            print(f"[FAIL] {failure}")


def _verify_stable_metrics(reports: list[VerificationReport]) -> None:
    """Fail multi-run verification when key aggregate metrics drift."""
    if len(reports) < 2:
        return
    baseline = reports[0].metrics
    drift_messages: list[str] = []
    for index, report in enumerate(reports[1:], start=2):
        metric_names = (set(baseline) | set(report.metrics)) - DRIFT_EXCLUDED_METRICS
        for metric_name in sorted(metric_names):
            message = _metric_drift_message(
                metric_name,
                baseline,
                report.metrics,
                index,
            )
            if message is not None:
                drift_messages.append(message)
    if not drift_messages:
        reports[-1].fact("stable metrics unchanged across verification runs")
        return
    for message in drift_messages:
        reports[-1].fail(message)


def _metric_drift_message(
    metric_name: str,
    baseline: dict[str, object],
    current: dict[str, object],
    run_index: int,
) -> str | None:
    """Return one drift failure message for a metric, if it changed."""
    baseline_value = baseline.get(metric_name)
    current_value = current.get(metric_name)
    if baseline_value == current_value:
        return None
    return (
        f"stable metric drift in run {run_index}: {metric_name} "
        f"expected {baseline_value!r}, got {current_value!r}"
    )


def _success_suffix(
    args: argparse.Namespace,
    reports: list[VerificationReport],
) -> str:
    """Build a concise success suffix for repeat and soak modes."""
    parts: list[str] = []
    if len(reports) > 1:
        parts.append(f"{len(reports)} runs")
    if args.soak_seconds:
        parts.append(f"{args.soak_seconds:g}s soak")
    return f" ({', '.join(parts)})" if parts else ""


def _positive_int(value: str) -> int:
    """Parse a positive integer CLI value."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return number


def _non_negative_float(value: str) -> float:
    """Parse a non-negative float CLI value."""
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return number


def _positive_float(value: str) -> float:
    """Parse a positive float CLI value."""
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return number


def _default_config_dir() -> Path:
    """Return the local HA config dir used by this workspace."""
    candidate = ROOT.parents[3] / "config" / "homeassistant-verify"
    return candidate if candidate.exists() else Path.cwd()
