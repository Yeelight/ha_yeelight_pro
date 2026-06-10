#!/usr/bin/env python3
"""Safely verify Yeelight Pro production APP scan-login behavior."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import importlib.util
import json
import types
import os
from pathlib import Path
import sys
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = ROOT / "custom_components" / "yeelight_pro"
SCAN_LOGIN_CONTRACT_PATH = (
    COMPONENT_ROOT / "scan_login_contract.py"
)

DEFAULT_DEVICE_ENV = "YEELIGHT_PRO_SCAN_LOGIN_DEVICE"
DEFAULT_REGION = "cn"
MAX_DURATION_SECONDS = 300.0
MAX_POLLS = 300
MIN_POLL_INTERVAL_SECONDS = 1.0


def _load_scan_login_contract() -> Any:
    """Load scan-login contract helpers without importing Home Assistant."""
    _ensure_probe_package()
    for module_name, path in (
        ("yeelight_pro_scan_login_probe.core.exceptions", COMPONENT_ROOT / "core" / "exceptions.py"),
        ("yeelight_pro_scan_login_probe.core.http_errors", COMPONENT_ROOT / "core" / "http_errors.py"),
        ("yeelight_pro_scan_login_probe.const", COMPONENT_ROOT / "const.py"),
        ("yeelight_pro_scan_login_probe.oauth_contract", COMPONENT_ROOT / "oauth_contract.py"),
    ):
        if module_name not in sys.modules:
            _load_probe_module(module_name, path)
    return _load_probe_module(
        "yeelight_pro_scan_login_probe.scan_login_contract",
        SCAN_LOGIN_CONTRACT_PATH,
    )


def _ensure_probe_package() -> None:
    """Create an isolated package namespace for relative contract imports."""
    package = sys.modules.get("yeelight_pro_scan_login_probe")
    if package is None:
        package = types.ModuleType("yeelight_pro_scan_login_probe")
        package.__path__ = [str(COMPONENT_ROOT)]  # type: ignore[attr-defined]
        sys.modules["yeelight_pro_scan_login_probe"] = package
    core_package = sys.modules.get("yeelight_pro_scan_login_probe.core")
    if core_package is None:
        core_package = types.ModuleType("yeelight_pro_scan_login_probe.core")
        core_package.__path__ = [str(COMPONENT_ROOT / "core")]  # type: ignore[attr-defined]
        sys.modules["yeelight_pro_scan_login_probe.core"] = core_package


def _load_probe_module(module_name: str, path: Path) -> Any:
    """Load a pure Yeelight contract module inside the isolated namespace."""
    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{path.name} module is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_scan_login_contract = _load_scan_login_contract()
SCAN_LOGIN_QRCODE_TTL_SECONDS = _scan_login_contract.SCAN_LOGIN_QRCODE_TTL_SECONDS
ScanLoginStatus = _scan_login_contract.ScanLoginStatus
account_base_url = _scan_login_contract.account_base_url
build_scan_login_qrcode_path = _scan_login_contract.build_scan_login_qrcode_path
build_scan_login_status_path = _scan_login_contract.build_scan_login_status_path
normalize_cloud_region = _scan_login_contract.normalize_cloud_region
parse_scan_login_response = _scan_login_contract.parse_scan_login_response


@dataclass(slots=True)
class RunSafety:
    """Safe result of CLI network-run validation."""

    allowed: bool
    region: str = DEFAULT_REGION
    device: str = ""
    error: str | None = None


@dataclass(slots=True)
class ScanLoginProbeSummary:
    """Diagnostics-safe aggregate summary for a scan-login probe."""

    ok: bool = False
    network_attempted: bool = False
    region: str = DEFAULT_REGION
    created_qrcode: bool = False
    polls: int = 0
    login_received: bool = False
    token_received: bool = False
    last_status: str | None = None
    remaining_seconds: int | None = None
    last_error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary without QR, device, token, or user data."""
        return {
            "ok": self.ok,
            "network_attempted": self.network_attempted,
            "region": self.region,
            "created_qrcode": self.created_qrcode,
            "polls": self.polls,
            "login_received": self.login_received,
            "token_received": self.token_received,
            "last_status": self.last_status,
            "remaining_seconds": self.remaining_seconds,
            "last_error_type": self.last_error_type,
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without accepting device or token values as arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify Yeelight Pro production APP scan-login behavior. "
            "The unique device value is read only from an environment variable."
        )
    )
    parser.add_argument(
        "--confirm-production-scan-login",
        action="store_true",
        help="Explicitly allow production scan-login HTTP requests.",
    )
    parser.add_argument(
        "--device-env",
        default=DEFAULT_DEVICE_ENV,
        help=(
            "Environment variable containing the scan-login device identifier. "
            f"Default: {DEFAULT_DEVICE_ENV}"
        ),
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help="Yeelight cloud region alias. One of cn, sg, us, de/eu.",
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=60.0,
        help=f"Maximum probe duration, capped at {int(MAX_DURATION_SECONDS)} seconds.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help=(
            "Seconds between QR status polls. "
            f"Minimum: {int(MIN_POLL_INTERVAL_SECONDS)} second."
        ),
    )
    parser.add_argument(
        "--max-polls",
        type=int,
        default=60,
        help=f"Maximum QR status polls, capped at {MAX_POLLS}.",
    )
    return parser


def validate_run_request(
    args: argparse.Namespace,
    environ: Mapping[str, str],
) -> RunSafety:
    """Fail closed unless the user explicitly enables production networking."""
    if not args.confirm_production_scan_login:
        return RunSafety(False, error="missing_confirm_flag")

    device_env = str(args.device_env).strip()
    device = str(environ.get(device_env, "")).strip()
    if not device:
        return RunSafety(False, error="missing_device_env")

    try:
        region = normalize_cloud_region(str(args.region))
    except Exception:
        return RunSafety(False, error="invalid_region")

    if args.duration_seconds <= 0 or args.duration_seconds > MAX_DURATION_SECONDS:
        return RunSafety(False, error="invalid_duration")
    if args.poll_interval_seconds < MIN_POLL_INTERVAL_SECONDS:
        return RunSafety(False, error="invalid_poll_interval")
    if args.max_polls <= 0 or args.max_polls > MAX_POLLS:
        return RunSafety(False, error="invalid_max_polls")

    return RunSafety(True, region=region, device=device)


async def async_probe_scan_login(
    *,
    region: str,
    device: str,
    duration_seconds: float,
    poll_interval_seconds: float,
    max_polls: int,
) -> ScanLoginProbeSummary:
    """Create and poll a production scan-login QR code with redacted output."""
    summary = ScanLoginProbeSummary(network_attempted=True, region=region)
    timeout = ClientTimeout(total=min(duration_seconds, MAX_DURATION_SECONDS))
    deadline = asyncio.get_running_loop().time() + duration_seconds
    try:
        async with aiohttp.ClientSession() as session:
            state = await _request_scan_login_state(
                session,
                timeout,
                region=region,
                path=build_scan_login_qrcode_path(device),
            )
            _update_summary_from_state(summary, state)
            summary.created_qrcode = True
            while (
                _state_pollable(state)
                and summary.polls < max_polls
                and asyncio.get_running_loop().time() < deadline
            ):
                await asyncio.sleep(poll_interval_seconds)
                if asyncio.get_running_loop().time() >= deadline:
                    break
                summary.polls += 1
                state = await _request_scan_login_state(
                    session,
                    timeout,
                    region=region,
                    path=build_scan_login_status_path(state.qr_code_id),
                )
                _update_summary_from_state(summary, state)
                if state.status == ScanLoginStatus.LOGIN:
                    break
        summary.ok = summary.login_received and summary.token_received
    except Exception as err:  # pragma: no cover - production network boundary
        summary.last_error_type = type(err).__name__
        summary.ok = False
    return summary


async def _request_scan_login_state(
    session: aiohttp.ClientSession,
    timeout: ClientTimeout,
    *,
    region: str,
    path: str,
) -> Any:
    """Request one scan-login state and parse it through the shared contract."""
    async with session.post(
        f"{account_base_url(region)}{path}",
        data={},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        payload = await response.json()
    if not isinstance(payload, Mapping):
        raise TypeError("scan-login response must be a JSON object")
    return parse_scan_login_response(payload)


def _update_summary_from_state(summary: ScanLoginProbeSummary, state: Any) -> None:
    """Copy only aggregate scan-login state into the summary."""
    summary.last_status = str(state.status)
    summary.remaining_seconds = state.remaining_seconds
    summary.login_received = state.status == ScanLoginStatus.LOGIN
    summary.token_received = state.token is not None


def _state_pollable(state: Any) -> bool:
    """Return whether the scan-login state should continue polling."""
    return bool(getattr(state, "pollable", False))


def _safe_failure(error: str | None) -> dict[str, Any]:
    """Return a JSON-safe failure response for CLI safety checks."""
    return {
        "ok": False,
        "network_attempted": False,
        "error": error or "unknown_error",
    }


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    safety = validate_run_request(args, os.environ)
    if not safety.allowed:
        print(json.dumps(_safe_failure(safety.error), sort_keys=True))
        return 2

    summary = asyncio.run(
        async_probe_scan_login(
            region=safety.region,
            device=safety.device,
            duration_seconds=args.duration_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
            max_polls=args.max_polls,
        )
    )
    print(json.dumps(summary.as_dict(), sort_keys=True))
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
