"""Runtime checks for the local Home Assistant container."""

from __future__ import annotations

import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .constants import BAD_LOG_MARKERS, YEELIGHT_LOG_MARKERS
from .report import VerificationReport
from .runtime_entities import verify_runtime_entity_counts


def verify_docker(container: str, report: VerificationReport) -> None:
    """Verify Docker container status."""
    result = _run(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
            container,
        ]
    )
    if result.returncode != 0:
        report.fail(f"docker container not inspectable: {container}")
        return
    status = result.stdout.strip()
    if "running" not in status or "healthy" not in status:
        report.fail(f"docker container is not healthy: {status or 'unknown'}")
    else:
        report.fact(f"docker container healthy: {container}")


def verify_ha_url(url: str, report: VerificationReport) -> None:
    """Verify the local HA frontend is reachable."""
    try:
        with urlopen(url, timeout=5) as response:
            code = response.getcode()
    except HTTPError as err:
        code = err.code
    except (OSError, URLError) as err:
        report.fail(f"HA URL is not reachable: {type(err).__name__}")
        return

    if 200 <= code < 500:
        report.fact(f"HA URL reachable: {url} ({code})")
    else:
        report.fail(f"HA URL returned unexpected status: {code}")


def verify_logs(container: str, report: VerificationReport, *, tail: int) -> None:
    """Verify recent container logs do not contain Yeelight Pro runtime failures."""
    result = _run(["docker", "logs", "--tail", str(tail), container], timeout=30)
    if result.returncode != 0:
        report.fail("docker logs could not be read")
        return

    lines = result.stdout.splitlines() + result.stderr.splitlines()
    bad_line_entries = [
        (index, line)
        for index, line in enumerate(lines)
        if any(marker in line for marker in YEELIGHT_LOG_MARKERS)
        and any(marker in line for marker in BAD_LOG_MARKERS)
    ]
    blocking_bad_lines, recovered_bad_lines = _split_blocking_yeelight_errors(
        bad_line_entries,
        lines,
    )
    text_platform_lines = [
        line
        for line in lines
        if "yeelight_pro" in line and ("text.py" in line or ".text" in line)
    ]
    if blocking_bad_lines:
        report.fail(
            f"Yeelight Pro unrecovered error log lines found: "
            f"{len(blocking_bad_lines)}"
        )
    else:
        report.fact("no Yeelight Pro ERROR/Traceback/import failures in logs")
    if recovered_bad_lines:
        report.fact(
            f"Yeelight Pro transient polling error log lines recovered: "
            f"{len(recovered_bad_lines)}"
        )
    if text_platform_lines:
        report.fail("Yeelight Pro text platform references found in logs")

    if any("Yeelight Pro integration setup complete" in line for line in lines):
        report.fact("setup completion log found")
    else:
        report.warn("setup completion log not found in selected log tail")


def verify_runtime_entities(
    container: str,
    report: VerificationReport,
    *,
    tail: int,
    expected_entity_counts: dict[str, int],
) -> None:
    """Verify active entity distribution from recent runtime logs."""
    result = _run(["docker", "logs", "--tail", str(tail), container], timeout=30)
    if result.returncode != 0:
        report.fail("docker logs could not be read for runtime entity counts")
        return
    lines = result.stdout.splitlines() + result.stderr.splitlines()
    verify_runtime_entity_counts(
        lines,
        report,
        expected_entity_counts=expected_entity_counts,
    )


def verify_synthetic_log_recovery(report: VerificationReport) -> None:
    """Verify transient polling recovery classification with synthetic log lines."""
    recovered_error = (
        "2026-06-07 ERROR (MainThread) "
        "[custom_components.yeelight_pro.core.coordinator] "
        "Error fetching yeelight_pro data: Connection error: ConnectionError"
    )
    recovered_marker = (
        "2026-06-07 INFO (MainThread) "
        "[custom_components.yeelight_pro.core.coordinator] "
        "Fetching yeelight_pro data recovered"
    )
    unrecovered_error = (
        "2026-06-07 ERROR (MainThread) "
        "[custom_components.yeelight_pro.core.coordinator] "
        "Error communicating with API while updating Yeelight Pro data: TimeoutError"
    )
    lines = [recovered_error, recovered_marker, unrecovered_error]
    bad_lines = [
        (index, line)
        for index, line in enumerate(lines)
        if any(marker in line for marker in YEELIGHT_LOG_MARKERS)
        and any(marker in line for marker in BAD_LOG_MARKERS)
    ]
    blocking, recovered = _split_blocking_yeelight_errors(bad_lines, lines)
    if len(recovered) != 1 or len(blocking) != 1:
        report.fail("synthetic runtime recovery classification failed")
        return
    report.fact("synthetic runtime recovery classification passed")
    report.metric("synthetic_runtime_recovery", "passed")


def _split_blocking_yeelight_errors(
    bad_lines: list[tuple[int, str]],
    all_lines: list[str],
) -> tuple[list[str], list[str]]:
    """Separate unrecovered failures from transient poll errors with recovery."""
    recovery_indices = {
        index
        for index, line in enumerate(all_lines)
        if "custom_components.yeelight_pro" in line
        and "Fetching yeelight_pro data recovered" in line
    }
    blocking: list[str] = []
    recovered: list[str] = []
    for index, bad_line in bad_lines:
        if _is_recoverable_poll_error(bad_line) and any(
            recovery_index > index for recovery_index in recovery_indices
        ):
            recovered.append(bad_line)
        else:
            blocking.append(bad_line)
    return blocking, recovered


def _is_recoverable_poll_error(line: str) -> bool:
    """Return true for coordinator polling failures HA later marks recovered."""
    recoverable_markers = (
        "Connection error while updating Yeelight Pro data",
        "Error communicating with API while updating Yeelight Pro data",
        "Error fetching yeelight_pro data",
    )
    fatal_markers = ("Traceback", "ImportError", "ModuleNotFoundError")
    return (
        "custom_components.yeelight_pro.core.coordinator" in line
        and any(marker in line for marker in recoverable_markers)
        and not any(marker in line for marker in fatal_markers)
    )


def _run(command: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and capture text output."""
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
