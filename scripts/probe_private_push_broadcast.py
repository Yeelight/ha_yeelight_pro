#!/usr/bin/env python3
"""Probe private push broadcast behavior with multiple WebSocket listeners."""

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
from aiohttp import WSMsgType

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
)
from custom_components.yeelight_pro.entry_migration import normalize_entry_data  # noqa: E402
from custom_components.yeelight_pro.push_contract import (  # noqa: E402
    PushMessageBuilder,
    build_push_url,
)
from scripts.private_push_probe.io_helpers import digest  # noqa: E402
from scripts.private_push_probe.models import ProbeSummary, TopologySnapshot  # noqa: E402
from scripts.private_push_probe.push_probe import handle_message, send_heartbeats  # noqa: E402
from scripts.private_push_probe.topology import fetch_topology  # noqa: E402
from scripts.probe_private_push_control_echo import (  # noqa: E402
    DEFAULT_CONFIG_DIR,
    DEFAULT_PROPERTY,
    DEFAULT_TARGET_NAME,
    _execute_probe_controls,
    _load_entry,
    _read_property_value,
    _resolve_device,
    _token_from_file,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Open multiple private WebSocket listeners and optionally write one "
            "device property to verify whether the service broadcasts the change."
        )
    )
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--entry-title", required=True)
    parser.add_argument("--listener-token-file", type=Path, default=None)
    parser.add_argument("--writer-token-file", type=Path, default=None)
    parser.add_argument("--writer-client-id", default="")
    parser.add_argument("--target-name", default=DEFAULT_TARGET_NAME)
    parser.add_argument("--device-id", default="")
    parser.add_argument("--property", default=DEFAULT_PROPERTY)
    parser.add_argument("--index", type=int, default=4)
    parser.add_argument("--listener-count", type=int, default=2)
    parser.add_argument("--duration-seconds", type=float, default=45.0)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--pre-control-delay-seconds", type=float, default=1.0)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--flip-restore", action="store_true")
    parser.add_argument("--restore-delay-seconds", type=float, default=3.0)
    parser.add_argument("--output", type=Path, default=None)
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    """Run the broadcast probe."""
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
    push_base_url = deployment_private_push_base_url(
        entry_data.get(CONF_PRIVATE_DOMAIN),
        entry_data.get(CONF_PRIVATE_PUSH_DOMAIN),
    )
    timing: dict[str, float] = {}
    started_at = time.monotonic()

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
        topology = await fetch_topology(
            session,
            entry_data,
            entry_options,
            config_dir=args.config_dir,
        )

        listener_tasks = [
            asyncio.create_task(
                _timed_probe_push(
                    session=session,
                    token=listener_token,
                    push_base_url=push_base_url,
                    topology=topology,
                    duration_seconds=args.duration_seconds,
                    max_frames=args.max_frames,
                    timing=timing,
                    listener_name=f"listener_{index + 1}",
                )
            )
            for index in range(args.listener_count)
        ]
        controls: list[dict[str, Any]] = []
        if args.execute:
            await asyncio.sleep(args.pre_control_delay_seconds)
            timing["control_monotonic"] = time.monotonic()
            controls = await _execute_probe_controls(
                client,
                house_id=house_id,
                device_id=int(device["id"]),
                property_name=args.property,
                index=args.index,
                current_value=current_value,
                flip_restore=bool(args.flip_restore),
                restore_delay_seconds=float(args.restore_delay_seconds),
            )
        listeners = await asyncio.gather(*listener_tasks)

    report = {
        "mode": "execute" if args.execute else "listen_only",
        "elapsed_seconds": round(time.monotonic() - started_at, 3),
        "target": {
            "name": device.get("name"),
            "id_hash": digest(device.get("id")),
            "property": args.property,
            "index": args.index,
            "current_value_type": type(current_value).__name__,
            "current_value": current_value,
        },
        "push_base_url_hash": digest(push_base_url),
        "listener_count": args.listener_count,
        "control": controls[0] if controls else None,
        "controls": controls,
        "listeners": listeners,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


async def _timed_probe_push(
    *,
    session: aiohttp.ClientSession,
    token: str,
    push_base_url: str,
    topology: TopologySnapshot,
    duration_seconds: float,
    max_frames: int,
    timing: Mapping[str, float],
    listener_name: str,
) -> dict[str, Any]:
    """Collect push frames and record first-data timing without raw payloads."""
    summary = ProbeSummary()
    builder = PushMessageBuilder()
    heartbeat_task: asyncio.Task[None] | None = None
    started_at = time.monotonic()
    deadline = started_at + duration_seconds
    first_frame_at: float | None = None
    first_data_at: float | None = None
    first_prop_at: float | None = None
    last_data_at: float | None = None
    try:
        async with session.ws_connect(build_push_url(token, base_url=push_base_url)) as ws:
            summary.connected = True
            await ws.send_json(builder.next_subscribe())
            summary.subscribe_sent = True
            heartbeat_task = asyncio.create_task(send_heartbeats(ws, builder, summary))
            while time.monotonic() < deadline and summary.frames_seen < max_frames:
                timeout = max(0.1, min(1.0, deadline - time.monotonic()))
                try:
                    message = await ws.receive(timeout=timeout)
                except TimeoutError:
                    summary.idle_timeouts += 1
                    continue
                if first_frame_at is None:
                    first_frame_at = time.monotonic()
                if message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED}:
                    summary.close_frames += 1
                    summary.last_close_code = getattr(ws, "close_code", None)
                    exception = ws.exception()
                    summary.last_close_exception_type = (
                        type(exception).__name__ if exception is not None else None
                    )
                    break
                if message.type is WSMsgType.ERROR:
                    summary.last_error_type = "WebSocketError"
                    summary.last_close_code = getattr(ws, "close_code", None)
                    exception = ws.exception()
                    summary.last_close_exception_type = (
                        type(exception).__name__ if exception is not None else None
                    )
                    break
                before_data = summary.data_frames
                before_prop = summary.prop_updates
                await handle_message(summary, topology, message)
                now = time.monotonic()
                if summary.data_frames > before_data:
                    first_data_at = first_data_at or now
                    last_data_at = now
                if summary.prop_updates > before_prop:
                    first_prop_at = first_prop_at or now
    except Exception as err:  # pragma: no cover - network boundary
        summary.last_error_type = type(err).__name__
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            except Exception as err:  # pragma: no cover - network boundary
                summary.last_error_type = type(err).__name__

    payload = summary.as_dict()
    control_at = timing.get("control_monotonic")
    return {
        "name": listener_name,
        "connected": payload.get("connected"),
        "subscribe_sent": payload.get("subscribe_sent"),
        "frames_seen": payload.get("frames_seen"),
        "control_frames": payload.get("control_frames"),
        "data_frames": payload.get("data_frames"),
        "prop_updates": payload.get("prop_updates"),
        "event_payloads": payload.get("event_payloads"),
        "matched_loaded_topology": payload.get("matched_loaded_topology"),
        "not_loaded": payload.get("not_loaded"),
        "maybe_filtered": payload.get("maybe_filtered"),
        "last_error_type": payload.get("last_error_type"),
        "last_close_code": payload.get("last_close_code"),
        "last_close_exception_type": payload.get("last_close_exception_type"),
        "first_frame_elapsed_seconds": _elapsed(first_frame_at, started_at),
        "first_data_elapsed_seconds": _elapsed(first_data_at, started_at),
        "first_prop_elapsed_seconds": _elapsed(first_prop_at, started_at),
        "last_data_elapsed_seconds": _elapsed(last_data_at, started_at),
        "first_data_after_control_seconds": _elapsed(first_data_at, control_at),
        "first_prop_after_control_seconds": _elapsed(first_prop_at, control_at),
        "update_samples": payload.get("update_samples"),
    }


def _elapsed(value: float | None, base: float | None) -> float | None:
    """Return a compact elapsed-second value."""
    if value is None or base is None:
        return None
    return round(value - base, 3)


def _validate_args(args: argparse.Namespace) -> None:
    """Validate probe safety and bounds."""
    if args.listener_count < 1 or args.listener_count > 4:
        raise SystemExit("--listener-count must be between 1 and 4")
    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be positive")
    if args.max_frames <= 0:
        raise SystemExit("--max-frames must be positive")
    if args.pre_control_delay_seconds < 0:
        raise SystemExit("--pre-control-delay-seconds must be non-negative")
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
