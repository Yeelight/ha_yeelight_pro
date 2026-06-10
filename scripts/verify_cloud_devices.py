#!/usr/bin/env python3
"""Safely verify Yeelight Pro production cloud device picker data."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_probe_client import (  # noqa: E402
    load_scan_login_contract as _load_probe_scan_login_contract,
    load_yeelight_client as _load_probe_client,
)

DEFAULT_ACCESS_TOKEN_ENV = "YEELIGHT_PRO_CLOUD_ACCESS_TOKEN"
DEFAULT_HOUSE_ID_ENV = "YEELIGHT_PRO_CLOUD_HOUSE_ID"
DEFAULT_CLIENT_ID_ENV = "YEELIGHT_PRO_CLOUD_CLIENT_ID"
DEFAULT_REGION = "cn"
MAX_TIMEOUT_SECONDS = 60


@dataclass(slots=True)
class RunSafety:
    """Safe result of CLI network-run validation."""

    allowed: bool
    region: str = DEFAULT_REGION
    domain: str = ""
    access_token: str = ""
    house_id: int = 0
    client_id: str = ""
    error: str | None = None


@dataclass(slots=True)
class CloudDevicesProbeSummary:
    """Diagnostics-safe aggregate summary for one cloud-device probe."""

    ok: bool = False
    network_attempted: bool = False
    region: str = DEFAULT_REGION
    device_count: int = 0
    has_devices: bool = False
    categories: Counter[str] = field(default_factory=Counter)
    last_error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary without token, house, or device values."""
        return {
            "ok": self.ok,
            "network_attempted": self.network_attempted,
            "region": self.region,
            "device_count": self.device_count,
            "has_devices": self.has_devices,
            "categories": dict(sorted(self.categories.items())),
            "last_error_type": self.last_error_type,
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without accepting token or house values."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify Yeelight Pro production cloud device picker data. "
            "Access token and house id are read only from environment variables."
        )
    )
    parser.add_argument(
        "--confirm-production-cloud-devices",
        action="store_true",
        help="Explicitly allow a production cloud devices read.",
    )
    parser.add_argument(
        "--access-token-env",
        default=DEFAULT_ACCESS_TOKEN_ENV,
        help=(
            "Environment variable containing the cloud access token. "
            f"Default: {DEFAULT_ACCESS_TOKEN_ENV}"
        ),
    )
    parser.add_argument(
        "--house-id-env",
        default=DEFAULT_HOUSE_ID_ENV,
        help=(
            "Environment variable containing the Yeelight house id. "
            f"Default: {DEFAULT_HOUSE_ID_ENV}"
        ),
    )
    parser.add_argument(
        "--client-id-env",
        default=DEFAULT_CLIENT_ID_ENV,
        help=(
            "Optional environment variable containing the Open API client id. "
            f"Default: {DEFAULT_CLIENT_ID_ENV}"
        ),
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help="Yeelight cloud region alias. One of cn, sg, us, de/eu.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help=f"Maximum probe timeout, capped at {MAX_TIMEOUT_SECONDS} seconds.",
    )
    return parser


def validate_run_request(
    args: argparse.Namespace,
    environ: Mapping[str, str],
) -> RunSafety:
    """Fail closed unless the user explicitly enables production networking."""
    if not args.confirm_production_cloud_devices:
        return RunSafety(False, error="missing_confirm_flag")

    access_token = str(environ.get(str(args.access_token_env).strip(), "")).strip()
    if not access_token:
        return RunSafety(False, error="missing_token_env")

    raw_house_id = str(environ.get(str(args.house_id_env).strip(), "")).strip()
    try:
        house_id = int(raw_house_id)
    except ValueError:
        return RunSafety(False, error="missing_house_id_env")
    if house_id <= 0:
        return RunSafety(False, error="missing_house_id_env")

    try:
        region = _normalize_cloud_region(str(args.region))
    except Exception:
        return RunSafety(False, error="invalid_region")

    if args.timeout_seconds <= 0 or args.timeout_seconds > MAX_TIMEOUT_SECONDS:
        return RunSafety(False, error="invalid_timeout")

    client_id = str(environ.get(str(args.client_id_env).strip(), "")).strip()
    return RunSafety(
        True,
        region=region,
        domain=_iot_domain_for_region(region),
        access_token=access_token,
        house_id=house_id,
        client_id=client_id,
    )


async def async_probe_cloud_devices(
    *,
    region: str,
    domain: str,
    access_token: str,
    house_id: int,
    client_id: str,
    timeout_seconds: float,
) -> CloudDevicesProbeSummary:
    """Read one production device list and return aggregate picker facts."""
    summary = CloudDevicesProbeSummary(network_attempted=True, region=region)
    client_class = _load_yeelight_client()
    try:
        async with aiohttp.ClientSession() as session:
            client = client_class(
                domain=domain,
                access_token=access_token,
                client_id=client_id,
                session=session,
                timeout=int(timeout_seconds),
            )
            devices = await client.get_devices(house_id)
        _update_summary_from_devices(summary, devices)
        summary.ok = True
    except Exception as err:  # pragma: no cover - production network boundary
        summary.last_error_type = type(err).__name__
        summary.ok = False
    return summary


def _update_summary_from_devices(
    summary: CloudDevicesProbeSummary,
    devices: Sequence[Mapping[str, Any]],
) -> None:
    """Copy only aggregate device-list facts into the summary."""
    summary.device_count = 0
    summary.categories.clear()
    for device in devices:
        if not isinstance(device, Mapping):
            continue
        summary.device_count += 1
        summary.categories[_device_category(device)] += 1
    summary.has_devices = summary.device_count > 0


def _device_category(device: Mapping[str, Any]) -> str:
    """Return a low-cardinality category for aggregate picker validation."""
    for key in ("category", "deviceCategory", "device_category", "type"):
        value = device.get(key)
        if value is not None:
            text = str(value).strip().lower()
            if text:
                return text
    return "unknown"


def _normalize_cloud_region(region: str) -> str:
    """Return the normalized Yeelight cloud region alias."""
    contract = _load_scan_login_contract()
    return str(contract.normalize_cloud_region(region))


def _iot_domain_for_region(region: str) -> str:
    """Return the documented Open API IoT domain for one region."""
    contract = _load_scan_login_contract()
    return str(contract.iot_base_url(region))


def _load_scan_login_contract() -> Any:
    """Load region helpers without importing Home Assistant."""
    return _load_probe_scan_login_contract()


def _load_yeelight_client() -> Any:
    """Load the HA-free production probe client after safety checks pass."""
    return _load_probe_client()


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
        async_probe_cloud_devices(
            region=safety.region,
            domain=safety.domain,
            access_token=safety.access_token,
            house_id=safety.house_id,
            client_id=safety.client_id,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(json.dumps(summary.as_dict(), sort_keys=True))
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
