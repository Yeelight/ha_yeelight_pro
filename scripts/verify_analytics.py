#!/usr/bin/env python3
"""Safely verify Yeelight Pro production analytics payload shape."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_analytics_support import (  # noqa: E402
    AnalyticsProbeSummary,
    analytics_request_path,
    iot_domain_for_region,
    load_yeelight_client,
    normalize_cloud_region,
    update_summary_from_payload,
)

DEFAULT_ACCESS_TOKEN_ENV = "YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN"
DEFAULT_HOUSE_ID_ENV = "YEELIGHT_PRO_ANALYTICS_HOUSE_ID"
DEFAULT_CLIENT_ID_ENV = "YEELIGHT_PRO_ANALYTICS_CLIENT_ID"
DEFAULT_REGION = "cn"
DEFAULT_ENDPOINT = "energy_analyse"
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
    endpoint: str = DEFAULT_ENDPOINT
    date_code: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    area_id: str | None = None
    error: str | None = None


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without accepting token or house values."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify Yeelight Pro production analytics payload shape. Access token "
            "and house id are read only from environment variables."
        )
    )
    parser.add_argument(
        "--confirm-production-analytics",
        action="store_true",
        help="Explicitly allow a production analytics read.",
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
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help="Analytics endpoint key, for example energy_analyse or action_day.",
    )
    parser.add_argument("--date-code")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--area-id-env")
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
    if not args.confirm_production_analytics:
        return RunSafety(False, error="missing_confirm_flag")

    access_token = str(environ.get(str(args.access_token_env).strip(), "")).strip()
    if not access_token:
        return RunSafety(False, error="missing_token_env")

    house_id = _house_id_from_env(args.house_id_env, environ)
    if house_id is None:
        return RunSafety(False, error="missing_house_id_env")

    try:
        region = normalize_cloud_region(str(args.region))
    except Exception:
        return RunSafety(False, error="invalid_region")

    area_id = _optional_env_value(args.area_id_env, environ)
    endpoint = str(args.endpoint).strip()
    try:
        analytics_request_path(
            house_id,
            endpoint,
            date_code=args.date_code,
            start_date=args.start_date,
            end_date=args.end_date,
            area_id=area_id,
        )
    except Exception:
        return RunSafety(False, error="invalid_analytics_request")

    if args.timeout_seconds <= 0 or args.timeout_seconds > MAX_TIMEOUT_SECONDS:
        return RunSafety(False, error="invalid_timeout")

    client_id = str(environ.get(str(args.client_id_env).strip(), "")).strip()
    return RunSafety(
        True,
        region=region,
        domain=iot_domain_for_region(region),
        access_token=access_token,
        house_id=house_id,
        client_id=client_id,
        endpoint=endpoint,
        date_code=args.date_code,
        start_date=args.start_date,
        end_date=args.end_date,
        area_id=area_id,
    )


async def async_probe_analytics(
    *,
    region: str,
    domain: str,
    access_token: str,
    house_id: int,
    client_id: str,
    endpoint: str,
    date_code: str | None,
    start_date: str | None,
    end_date: str | None,
    area_id: str | None,
    timeout_seconds: float,
) -> AnalyticsProbeSummary:
    """Read one production analytics endpoint and return aggregate facts."""
    summary = AnalyticsProbeSummary(
        network_attempted=True,
        region=region,
        endpoint=endpoint,
    )
    client_class = load_yeelight_client()
    try:
        async with aiohttp.ClientSession() as session:
            client = client_class(
                domain=domain,
                access_token=access_token,
                client_id=client_id,
                session=session,
                timeout=int(timeout_seconds),
            )
            payload = await client.request_analytics(
                house_id=house_id,
                endpoint_key=endpoint,
                date_code=date_code,
                start_date=start_date,
                end_date=end_date,
                area_id=area_id,
            )
        update_summary_from_payload(summary, payload)
        summary.ok = True
    except Exception as err:  # pragma: no cover - production network boundary
        summary.last_error_type = type(err).__name__
        summary.ok = False
    return summary


def _house_id_from_env(name: str, environ: Mapping[str, str]) -> int | None:
    """Return a positive house id from the configured environment variable."""
    raw_house_id = str(environ.get(str(name).strip(), "")).strip()
    try:
        house_id = int(raw_house_id)
    except ValueError:
        return None
    return house_id if house_id > 0 else None


def _optional_env_value(name: str | None, environ: Mapping[str, str]) -> str | None:
    """Return an optional value from an environment variable name."""
    if name is None:
        return None
    env_name = str(name).strip()
    if not env_name:
        return None
    value = str(environ.get(env_name, "")).strip()
    return value or None


def _safe_failure(error: str | None) -> dict[str, object]:
    """Return a JSON-safe failure response for CLI safety checks."""
    return {
        "ok": False,
        "network_attempted": False,
        "error": error or "unknown_error",
    }


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    safety = validate_run_request(args, os.environ)
    if not safety.allowed:
        print(json.dumps(_safe_failure(safety.error), sort_keys=True))
        return 2

    summary = asyncio.run(
        async_probe_analytics(
            region=safety.region,
            domain=safety.domain,
            access_token=safety.access_token,
            house_id=safety.house_id,
            client_id=safety.client_id,
            endpoint=safety.endpoint,
            date_code=safety.date_code,
            start_date=safety.start_date,
            end_date=safety.end_date,
            area_id=safety.area_id,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(json.dumps(summary.as_dict(), sort_keys=True))
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
