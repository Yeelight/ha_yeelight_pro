"""CLI for the private push topology probe."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlsplit

import aiohttp

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_components.yeelight_pro.const import (  # noqa: E402
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CLOUD_REGION_PUSH_BASE_URLS,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_REGION,
)
from custom_components.yeelight_pro.deployment_urls import (  # noqa: E402
    deployment_private_push_base_url,
    deployment_push_base_url,
)
from custom_components.yeelight_pro.device_filter import (  # noqa: E402
    normalize_device_import_filter,
    preview_device_import_filter,
)
from custom_components.yeelight_pro.entry_migration import (  # noqa: E402
    normalize_entry_data,
)
from scripts.private_push_probe.io_helpers import digest  # noqa: E402
from scripts.private_push_probe.models import ProbeSummary, TopologySnapshot  # noqa: E402
from scripts.private_push_probe.push_probe import probe_push  # noqa: E402
from scripts.private_push_probe.topology import (  # noqa: E402
    fetch_topology,
    topology_payload_coverage,
    topology_self_check,
)

DEFAULT_CONFIG_DIR = Path(
    "/Users/yeelight/Desktop/workspace/ai/lucore/config/homeassistant-verify"
)
MAX_DURATION_SECONDS = 180.0
MAX_FRAMES = 500


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Probe Yeelight Pro private push payload topology matching."
    )
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--entry-id", default="")
    parser.add_argument("--entry-title", default="")
    parser.add_argument("--push-base-url", default="")
    parser.add_argument("--duration-seconds", type=float, default=75.0)
    parser.add_argument("--max-frames", type=int, default=80)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--unsafe-local-details",
        action="store_true",
        help=(
            "Include raw local node ids/names in the report. Use only for "
            "manual private debugging; do not publish the output."
        ),
    )
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    """Run the probe and print a redacted JSON report."""
    args = build_parser().parse_args(argv)
    validate_bounds(args.duration_seconds, args.max_frames)
    entry = load_target_entry(
        args.config_dir,
        entry_id=args.entry_id,
        entry_title=args.entry_title,
    )
    entry_data = normalize_entry_data(entry.get("data") or {})
    entry_options = entry.get("options") or {}
    async with aiohttp.ClientSession() as session:
        topology = await fetch_topology(
            session,
            entry_data,
            entry_options,
            config_dir=args.config_dir,
        )
        selected_push_base_url = push_base_url(entry_data, args.push_base_url)
        summary = await probe_push(
            session=session,
            token=str(entry_data.get(CONF_ACCESS_TOKEN) or ""),
            push_base_url=selected_push_base_url,
            topology=topology,
            duration_seconds=float(args.duration_seconds),
            max_frames=int(args.max_frames),
            unsafe_local_details=bool(args.unsafe_local_details),
        )
    report = build_report(
        entry,
        entry_data,
        topology,
        summary,
        selected_push_base_url,
        unsafe_local_details=bool(args.unsafe_local_details),
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary.last_error_type is None else 1


def build_report(
    entry: Mapping[str, Any],
    entry_data: Mapping[str, Any],
    topology: TopologySnapshot,
    summary: ProbeSummary,
    selected_push_base_url: str,
    *,
    unsafe_local_details: bool = False,
) -> dict[str, Any]:
    """Build the redacted report."""
    normalized_filter = normalize_device_import_filter(topology.filter_config)
    preview = preview_device_import_filter(topology.data.values(), topology.filter_config)
    return {
        "entry": {
            "entry_id_hash": digest(entry.get("entry_id")),
            "mode": entry_data.get(CONF_CONNECTION_MODE),
            "house_id_hash": digest(entry_data.get(CONF_HOUSE_ID)),
            "private_push_configured": bool(entry_data.get(CONF_PRIVATE_PUSH_DOMAIN)),
        },
        "report_safety": {
            "unsafe_local_details": unsafe_local_details,
        },
        "push_endpoint": push_endpoint_summary(selected_push_base_url),
        "topology": {
            "devices": len(topology.data),
            "gateways": len(topology.gateways),
            "groups": len(topology.groups),
            "rooms": len(topology.rooms),
            "areas": len(topology.areas),
            "houses": len(topology.houses),
            "loaded_topology_hash_count": topology.hash_count,
            "hydration": dict(topology.hydration),
            "endpoint_errors": dict(sorted(topology.endpoint_errors.items())),
            "self_check": topology_self_check(topology),
            "synthetic_payload_coverage": topology_payload_coverage(topology),
        },
        "device_import_filter": {
            **preview.as_dict(),
            "normalized_enabled": normalized_filter.enabled,
        },
        "push": summary.as_dict(),
    }


def push_base_url(data: Mapping[str, Any], override: str) -> str:
    """Return push base URL from override or entry data."""
    if override.strip():
        return deployment_push_base_url(override)
    mode = data.get(CONF_CONNECTION_MODE)
    if mode == CONNECTION_MODE_CLOUD:
        region = str(data.get(CONF_CLOUD_REGION) or DEFAULT_CLOUD_REGION)
        return CLOUD_REGION_PUSH_BASE_URLS.get(
            region,
            CLOUD_REGION_PUSH_BASE_URLS[DEFAULT_CLOUD_REGION],
        )
    private_push = data.get(CONF_PRIVATE_PUSH_DOMAIN)
    return deployment_private_push_base_url(data.get(CONF_PRIVATE_DOMAIN), private_push)


def push_endpoint_summary(base_url: str) -> dict[str, Any]:
    """Return a redacted push endpoint summary for probe evidence."""
    parsed = urlsplit(base_url)
    netloc = parsed.netloc.casefold()
    host = (parsed.hostname or "").casefold()
    return {
        "scheme": parsed.scheme,
        "path": parsed.path,
        "host_hash": digest(netloc),
        "known_route": _known_push_route(host, netloc),
    }


def _known_push_route(host: str, netloc: str) -> str:
    """Return a stable label for known private push lab routes."""
    if host == "192.168.1.202" or netloc == "192.168.1.202:7779":
        return "private_dev_direct"
    if host == "192.168.0.89" or netloc == "192.168.0.89:7779":
        return "private_test_direct"
    if host.endswith(".yeelight.com"):
        return "public_cloud"
    return "custom"


def load_target_entry(
    config_dir: Path,
    *,
    entry_id: str,
    entry_title: str,
) -> dict[str, Any]:
    """Load a cloud/private Yeelight Pro config entry from HA storage."""
    payload = json.loads(
        (config_dir / ".storage" / "core.config_entries").read_text(encoding="utf-8")
    )
    candidates: list[dict[str, Any]] = []
    for entry in payload.get("data", {}).get("entries", []):
        if not isinstance(entry, dict) or entry.get("domain") != "yeelight_pro":
            continue
        data = normalize_entry_data(entry.get("data") or {})
        if data.get(CONF_CONNECTION_MODE) in {CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE}:
            candidates.append(entry)
    for entry in candidates:
        if entry_id and entry.get("entry_id") == entry_id:
            return entry
        if entry_title and entry.get("title") == entry_title:
            return entry
    if len(candidates) == 1 and not entry_id and not entry_title:
        return candidates[0]
    raise SystemExit("target Yeelight Pro cloud/private config entry not found")


def validate_bounds(duration_seconds: float, max_frames: int) -> None:
    """Validate probe safety bounds."""
    if duration_seconds <= 0 or duration_seconds > MAX_DURATION_SECONDS:
        raise SystemExit("invalid duration")
    if max_frames <= 0 or max_frames > MAX_FRAMES:
        raise SystemExit("invalid max frames")


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous CLI wrapper."""
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
