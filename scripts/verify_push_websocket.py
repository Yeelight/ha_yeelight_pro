#!/usr/bin/env python3
"""Safely verify Yeelight Pro production WebSocket push behavior."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import aiohttp
from aiohttp import WSMsgType

ROOT = Path(__file__).resolve().parents[1]
PUSH_CONTRACT_PATH = ROOT / "custom_components" / "yeelight_pro" / "push_contract.py"

_push_contract = None

DEFAULT_TOKEN_ENV = "YEELIGHT_PRO_PUSH_TOKEN"
MAX_DURATION_SECONDS = 300.0
MAX_FRAMES = 1000


def _load_push_contract() -> Any:
    """Load the pure push contract helper without importing Home Assistant."""
    spec = importlib.util.spec_from_file_location(
        "yeelight_pro_push_contract_probe",
        PUSH_CONTRACT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("push_contract module is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_push_contract = _load_push_contract()
CONTROL_METHODS = _push_contract.PUSH_CONTROL_METHODS
DATA_TYPES = _push_contract.PUSH_DATA_TYPES
PUSH_HEARTBEAT_INTERVAL_SECONDS = _push_contract.PUSH_HEARTBEAT_INTERVAL_SECONDS
PushMessageBuilder = _push_contract.PushMessageBuilder
build_push_url = _push_contract.build_push_url


@dataclass(slots=True)
class RunSafety:
    """Safe result of CLI network-run validation."""

    allowed: bool
    token: str = ""
    error: str | None = None


@dataclass(slots=True)
class PushWebSocketProbeSummary:
    """Diagnostics-safe aggregate summary for a WebSocket probe."""

    ok: bool = False
    network_attempted: bool = False
    frames_seen: int = 0
    data_frames: int = 0
    control_ack_frames: int = 0
    control_error_frames: int = 0
    other_json_frames: int = 0
    parse_error_frames: int = 0
    text_frames: int = 0
    binary_frames: int = 0
    close_frames: int = 0
    sent_subscribe: bool = False
    sent_heartbeats: int = 0
    last_error_type: str | None = None
    data_types: Counter[str] = field(default_factory=Counter)
    control_methods: Counter[str] = field(default_factory=Counter)
    json_shapes: Counter[str] = field(default_factory=Counter)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary without payload values or endpoint data."""
        return {
            "ok": self.ok,
            "network_attempted": self.network_attempted,
            "frames_seen": self.frames_seen,
            "data_frames": self.data_frames,
            "control_ack_frames": self.control_ack_frames,
            "control_error_frames": self.control_error_frames,
            "other_json_frames": self.other_json_frames,
            "parse_error_frames": self.parse_error_frames,
            "text_frames": self.text_frames,
            "binary_frames": self.binary_frames,
            "close_frames": self.close_frames,
            "sent_subscribe": self.sent_subscribe,
            "sent_heartbeats": self.sent_heartbeats,
            "last_error_type": self.last_error_type,
            "data_types": dict(sorted(self.data_types.items())),
            "control_methods": dict(sorted(self.control_methods.items())),
            "json_shapes": dict(sorted(self.json_shapes.items())),
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without accepting token material as arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify Yeelight Pro production WebSocket push behavior. "
            "The token is read only from an environment variable."
        )
    )
    parser.add_argument(
        "--confirm-production-websocket",
        action="store_true",
        help="Explicitly allow a production WebSocket connection.",
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help=f"Environment variable containing the bearer token. Default: {DEFAULT_TOKEN_ENV}",
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=30.0,
        help=f"Maximum probe duration, capped at {int(MAX_DURATION_SECONDS)} seconds.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=20,
        help=f"Maximum received WebSocket frames, capped at {MAX_FRAMES}.",
    )
    return parser


def validate_run_request(
    args: argparse.Namespace,
    environ: Mapping[str, str],
) -> RunSafety:
    """Fail closed unless the user explicitly enables production networking."""
    if not args.confirm_production_websocket:
        return RunSafety(False, error="missing_confirm_flag")

    token_env = str(args.token_env).strip()
    token = str(environ.get(token_env, "")).strip()
    if not token:
        return RunSafety(False, error="missing_token_env")

    if args.duration_seconds <= 0 or args.duration_seconds > MAX_DURATION_SECONDS:
        return RunSafety(False, error="invalid_duration")
    if args.max_frames <= 0 or args.max_frames > MAX_FRAMES:
        return RunSafety(False, error="invalid_max_frames")

    return RunSafety(True, token=token)


def update_summary_from_payload(
    summary: PushWebSocketProbeSummary,
    payload: Mapping[str, Any],
) -> None:
    """Classify one JSON object frame without copying payload values."""
    summary.json_shapes[_shape_key(payload)] += 1
    method = payload.get("method")
    payload_type = payload.get("type")
    if method in CONTROL_METHODS:
        method_name = str(method)
        summary.control_methods[method_name] += 1
        success = payload.get("success")
        code = str(payload.get("code", "")).strip()
        if success is False or code not in ("", "200"):
            summary.control_error_frames += 1
        else:
            summary.control_ack_frames += 1
        return

    if payload_type in DATA_TYPES:
        data_type = str(payload_type)
        summary.data_types[data_type] += 1
        summary.data_frames += 1
        return

    summary.other_json_frames += 1


async def async_probe_push_websocket(
    *,
    token: str,
    duration_seconds: float,
    max_frames: int,
) -> PushWebSocketProbeSummary:
    """Connect to the documented push endpoint and return aggregate facts."""
    summary = PushWebSocketProbeSummary(network_attempted=True)
    message_builder = PushMessageBuilder()
    heartbeat_task: asyncio.Task[None] | None = None
    deadline = time.monotonic() + duration_seconds
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(build_push_url(token)) as websocket:
                await websocket.send_json(message_builder.next_subscribe())
                summary.sent_subscribe = True
                heartbeat_task = asyncio.create_task(
                    _send_heartbeats(websocket, message_builder, summary)
                )
                while time.monotonic() < deadline and summary.frames_seen < max_frames:
                    timeout = max(0.1, min(1.0, deadline - time.monotonic()))
                    message = await websocket.receive(timeout=timeout)
                    if message.type is WSMsgType.CLOSED:
                        summary.close_frames += 1
                        break
                    if message.type is WSMsgType.CLOSE:
                        summary.close_frames += 1
                        break
                    if message.type is WSMsgType.ERROR:
                        summary.last_error_type = "WebSocketError"
                        break
                    _update_summary_from_ws_message(summary, message)
                    if summary.control_error_frames:
                        break
        summary.ok = summary.last_error_type is None and summary.control_error_frames == 0
    except Exception as err:  # pragma: no cover - production network boundary
        summary.last_error_type = type(err).__name__
        summary.ok = False
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            except Exception as err:  # pragma: no cover - production network boundary
                summary.last_error_type = type(err).__name__
                summary.ok = False
    return summary


async def _send_heartbeats(
    websocket: Any,
    message_builder: Any,
    summary: PushWebSocketProbeSummary,
) -> None:
    """Send documented heartbeat frames while the probe is active."""
    while True:
        await asyncio.sleep(PUSH_HEARTBEAT_INTERVAL_SECONDS)
        await websocket.send_json(message_builder.next_heartbeat())
        summary.sent_heartbeats += 1


def _update_summary_from_ws_message(
    summary: PushWebSocketProbeSummary,
    message: Any,
) -> None:
    """Update aggregate counters from one aiohttp WebSocket message."""
    if message.type is WSMsgType.TEXT:
        summary.text_frames += 1
    elif message.type is WSMsgType.BINARY:
        summary.binary_frames += 1
    else:
        return

    summary.frames_seen += 1
    data = message.data
    if isinstance(data, bytes):
        try:
            data = data.decode()
        except UnicodeDecodeError:
            summary.parse_error_frames += 1
            return
    if not isinstance(data, str):
        summary.parse_error_frames += 1
        return
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        summary.parse_error_frames += 1
        return
    if not isinstance(payload, dict):
        summary.parse_error_frames += 1
        return
    update_summary_from_payload(summary, payload)


def _shape_key(payload: Mapping[str, Any]) -> str:
    """Return a field-name-only shape key for a JSON object."""
    safe_keys = sorted(str(key) for key in payload)
    return ",".join(safe_keys) if safe_keys else "<empty>"


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
        async_probe_push_websocket(
            token=safety.token,
            duration_seconds=args.duration_seconds,
            max_frames=args.max_frames,
        )
    )
    print(json.dumps(summary.as_dict(), sort_keys=True))
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
