#!/usr/bin/env python3
"""Probe whether a private Open API write is echoed through WebSocket push."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
import time
from typing import Any

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.yeelight_pro.const import (  # noqa: E402
    CONF_ACCESS_TOKEN,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
)
from custom_components.yeelight_pro.core.client import YeelightProClient  # noqa: E402
from custom_components.yeelight_pro.deployment_urls import (  # noqa: E402
    deployment_iot_base_url,
    deployment_private_push_base_url,
    deployment_push_base_url,
)
from custom_components.yeelight_pro.entry_migration import normalize_entry_data  # noqa: E402
from scripts.private_push_probe.io_helpers import digest  # noqa: E402
from scripts.private_push_probe.push_probe import probe_push  # noqa: E402
from scripts.private_push_probe.topology import fetch_topology  # noqa: E402

DEFAULT_CONFIG_DIR = Path(
    "/Users/yeelight/Desktop/workspace/ai/lucore/config/homeassistant-verify"
)
DEFAULT_TARGET_NAME = "relay_switch-智能开关-四键 (rtl8762e版)-854041-01"
DEFAULT_PROPERTY = "p"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Read a private Yeelight device property and optionally write the "
            "same value, or flip and restore a boolean value, while listening "
            "for WebSocket push echo."
        )
    )
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--entry-title", required=True)
    parser.add_argument(
        "--listener-token-file",
        type=Path,
        default=None,
        help=(
            "Optional file containing the WebSocket listener token. Defaults to "
            "the config-entry access token."
        ),
    )
    parser.add_argument(
        "--writer-token-file",
        type=Path,
        default=None,
        help=(
            "Optional file containing the Open API writer token. Defaults to "
            "the config-entry access token."
        ),
    )
    parser.add_argument(
        "--writer-client-id",
        default="",
        help=(
            "Optional Open API writer client id. Defaults to the config-entry "
            "client id."
        ),
    )
    parser.add_argument("--target-name", default=DEFAULT_TARGET_NAME)
    parser.add_argument("--device-id", default="")
    parser.add_argument("--property", default=DEFAULT_PROPERTY)
    parser.add_argument("--index", type=int, default=4)
    parser.add_argument("--duration-seconds", type=float, default=45.0)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument(
        "--push-base-url",
        default="",
        help="Optional WebSocket push URL override for diagnostics.",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--flip-restore",
        action="store_true",
        help=(
            "Temporarily flip a boolean value and restore it before the probe "
            "exits. Requires --execute."
        ),
    )
    parser.add_argument(
        "--restore-delay-seconds",
        type=float,
        default=3.0,
        help="Seconds to wait before restoring a flipped boolean value.",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    """Run the control echo probe."""
    args = build_parser().parse_args(argv)
    _validate_args(args)
    entry = _load_entry(args.config_dir, args.entry_title)
    entry_data = normalize_entry_data(entry.get("data") or {})
    entry_options = entry.get("options") or {}
    listener_token = _token_from_file(
        args.listener_token_file,
        fallback=str(entry_data.get(CONF_ACCESS_TOKEN) or ""),
    )
    writer_token = _token_from_file(
        args.writer_token_file,
        fallback=str(entry_data.get(CONF_ACCESS_TOKEN) or ""),
    )
    writer_client_id = (
        str(args.writer_client_id).strip()
        or str(entry_data.get(CONF_OPEN_API_CLIENT_ID) or "")
    )

    async with aiohttp.ClientSession() as session:
        client = YeelightProClient(
            domain=deployment_iot_base_url(entry_data.get(CONF_PRIVATE_DOMAIN)),
            access_token=writer_token,
            client_id=writer_client_id,
            session=session,
        )
        house_id = int(entry_data[CONF_HOUSE_ID])
        device = await _resolve_device(
            client,
            house_id=house_id,
            device_id=args.device_id,
            target_name=args.target_name,
        )
        current = await client.read_node_properties(
            house_id=house_id,
            node_kind="device",
            resource_id=int(device["id"]),
            properties=[args.property],
            index=args.index,
        )
        current_value = _read_property_value(current, args.property)
        push_base_url = _push_base_url(entry_data, override=args.push_base_url)
        before_report = {
            "mode": "execute" if args.execute else "dry_run",
            "target": {
                "name": device.get("name"),
                "id_hash": digest(device.get("id")),
                "property": args.property,
                "index": args.index,
                "current_value_type": type(current_value).__name__,
                "current_value": current_value,
            },
            "push_base_url_hash": digest(push_base_url),
        }

        control_results: list[dict[str, Any]] = []
        started_at = time.monotonic()
        if args.execute:
            topology = await fetch_topology(
                session,
                entry_data,
                entry_options,
                config_dir=args.config_dir,
            )
            listen_task = asyncio.create_task(
                _probe_push(
                    session=session,
                    token=listener_token,
                    push_base_url=push_base_url,
                    topology=topology,
                    duration_seconds=args.duration_seconds,
                    max_frames=args.max_frames,
                )
            )
            await asyncio.sleep(1.0)
            control_results = await _execute_probe_controls(
                client,
                house_id=house_id,
                device_id=int(device["id"]),
                property_name=args.property,
                index=args.index,
                current_value=current_value,
                flip_restore=bool(args.flip_restore),
                restore_delay_seconds=float(args.restore_delay_seconds),
            )
            push_summary = await listen_task
        else:
            push_summary = None

    report = {
        **before_report,
        "elapsed_seconds": round(time.monotonic() - started_at, 3),
        "control": control_results[0] if control_results else None,
        "controls": control_results,
        "push": push_summary,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


async def _execute_probe_controls(
    client: YeelightProClient,
    *,
    house_id: int,
    device_id: int,
    property_name: str,
    index: int,
    current_value: Any,
    flip_restore: bool,
    restore_delay_seconds: float,
) -> list[dict[str, Any]]:
    """Run write probes and always restore boolean flip probes."""
    if not flip_restore:
        result = await _write_property(
            client,
            house_id=house_id,
            device_id=device_id,
            property_name=property_name,
            index=index,
            value=current_value,
        )
        return [_safe_control_result("same_value", result)]

    flipped_value = not current_value
    results: list[dict[str, Any]] = []
    try:
        flipped = await _write_property(
            client,
            house_id=house_id,
            device_id=device_id,
            property_name=property_name,
            index=index,
            value=flipped_value,
        )
        results.append(_safe_control_result("flip", flipped))
        await asyncio.sleep(restore_delay_seconds)
    finally:
        restored = await _write_property(
            client,
            house_id=house_id,
            device_id=device_id,
            property_name=property_name,
            index=index,
            value=current_value,
        )
        results.append(_safe_control_result("restore", restored))
    return results


async def _write_property(
    client: YeelightProClient,
    *,
    house_id: int,
    device_id: int,
    property_name: str,
    index: int,
    value: Any,
) -> Mapping[str, Any]:
    """Write one indexed device property."""
    return await client.control_node_properties(
        house_id=house_id,
        node_kind="device",
        resource_id=device_id,
        command="set",
        params={property_name: value},
        index=index,
        duration=0,
    )


async def _probe_push(
    *,
    session: aiohttp.ClientSession,
    token: str,
    push_base_url: str,
    topology: Any,
    duration_seconds: float,
    max_frames: int,
) -> dict[str, Any]:
    """Run the existing topology-aware push probe and return its summary."""
    summary = await probe_push(
        session=session,
        token=token,
        push_base_url=push_base_url,
        topology=topology,
        duration_seconds=duration_seconds,
        max_frames=max_frames,
    )
    payload = summary.as_dict()
    return {
        key: payload.get(key)
        for key in (
            "connected",
            "subscribe_sent",
            "frames_seen",
            "control_frames",
            "data_frames",
            "prop_updates",
            "event_payloads",
            "matched_loaded_topology",
            "not_loaded",
            "maybe_filtered",
            "last_error_type",
            "last_close_code",
            "last_close_exception_type",
            "update_samples",
        )
    }


async def _resolve_device(
    client: YeelightProClient,
    *,
    house_id: int,
    device_id: str,
    target_name: str,
) -> Mapping[str, Any]:
    """Resolve a device by id or exact name."""
    devices = await client.get_devices(house_id)
    if device_id:
        for device in devices:
            if str(device.get("id")) == str(device_id):
                return device
        raise SystemExit("target device id not found")
    matches = [device for device in devices if str(device.get("name") or "") == target_name]
    if len(matches) != 1:
        raise SystemExit(f"target device name matched {len(matches)} devices")
    return matches[0]


def _read_property_value(payload: Mapping[str, Any], prop: str) -> Any:
    """Extract a property value from Open API read response."""
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise SystemExit("read response does not contain data list")
    for row in rows:
        if isinstance(row, Mapping) and row.get("propId") == prop:
            return row.get("value")
    raise SystemExit(f"property {prop!r} not found in read response")


def _push_base_url(data: Mapping[str, Any], *, override: str = "") -> str:
    """Return private push base URL from config-entry data."""
    if override.strip():
        return deployment_push_base_url(override)
    private_domain = data.get(CONF_PRIVATE_DOMAIN)
    private_push = data.get(CONF_PRIVATE_PUSH_DOMAIN)
    return deployment_private_push_base_url(private_domain, private_push)


def _safe_control_result(step: str, value: Mapping[str, Any]) -> dict[str, Any]:
    """Return diagnostics-safe control result fields."""
    return {
        "step": step,
        "success": value.get("success"),
        "code": value.get("code"),
        "msg": value.get("msg"),
    }


def _load_entry(config_dir: Path, entry_title: str) -> dict[str, Any]:
    """Load a Yeelight Pro config entry by title."""
    payload = json.loads(
        (config_dir / ".storage" / "core.config_entries").read_text(encoding="utf-8")
    )
    matches = [
        entry
        for entry in payload.get("data", {}).get("entries", [])
        if isinstance(entry, dict)
        and entry.get("domain") == "yeelight_pro"
        and entry.get("title") == entry_title
    ]
    if len(matches) != 1:
        raise SystemExit(f"entry title matched {len(matches)} entries")
    return matches[0]


def _token_from_file(path: Path | None, *, fallback: str) -> str:
    """Read an optional token file without ever logging the token value."""
    if path is None:
        return fallback
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit(f"token file is empty: {path}")
    return token


def _validate_args(args: argparse.Namespace) -> None:
    """Validate mode and safety arguments."""
    if args.flip_restore and not args.execute:
        raise SystemExit("--flip-restore requires --execute")
    if args.flip_restore and args.property != DEFAULT_PROPERTY:
        raise SystemExit("--flip-restore currently supports boolean property p only")
    if args.restore_delay_seconds < 0:
        raise SystemExit("--restore-delay-seconds must be non-negative")


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous CLI wrapper."""
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
