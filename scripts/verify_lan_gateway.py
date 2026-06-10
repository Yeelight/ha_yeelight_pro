#!/usr/bin/env python3
"""Safely verify Yeelight Pro production LAN gateway TCP behavior."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
import os
from typing import Any

DEFAULT_HOST_ENV = "YEELIGHT_PRO_LAN_GATEWAY_HOST"
DEFAULT_PORT_ENV = "YEELIGHT_PRO_LAN_GATEWAY_PORT"
DEFAULT_PORT = 65443
MAX_TIMEOUT_SECONDS = 60.0
MAX_FRAMES = 100
LAN_FRAME_SEPARATOR = "\r\n"
METHOD_GET_TOPOLOGY = "gateway_get.topology"
LAN_PUSH_METHODS = {
    "gateway_post.topology",
    "gateway_post.prop",
    "gateway_post.event",
}


@dataclass(slots=True)
class RunSafety:
    """Safe result of CLI network-run validation."""

    allowed: bool
    host: str = ""
    port: int = DEFAULT_PORT
    timeout_seconds: float = 0.0
    max_frames: int = 0
    error: str | None = None


@dataclass(slots=True)
class LanGatewayProbeSummary:
    """Diagnostics-safe aggregate summary for one LAN gateway probe."""

    ok: bool = False
    network_attempted: bool = False
    connected: bool = False
    sent_topology_request: bool = False
    frames_seen: int = 0
    topology_frames: int = 0
    property_frames: int = 0
    event_frames: int = 0
    other_json_frames: int = 0
    parse_error_frames: int = 0
    last_error_type: str | None = None
    methods: Counter[str] = field(default_factory=Counter)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary without host, device, or payload values."""
        return {
            "ok": self.ok,
            "network_attempted": self.network_attempted,
            "connected": self.connected,
            "sent_topology_request": self.sent_topology_request,
            "frames_seen": self.frames_seen,
            "topology_frames": self.topology_frames,
            "property_frames": self.property_frames,
            "event_frames": self.event_frames,
            "other_json_frames": self.other_json_frames,
            "parse_error_frames": self.parse_error_frames,
            "last_error_type": self.last_error_type,
            "methods": dict(sorted(self.methods.items())),
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without accepting LAN host values directly."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify Yeelight Pro LAN gateway TCP behavior. The gateway host is "
            "read only from an environment variable."
        )
    )
    parser.add_argument(
        "--confirm-production-lan-gateway",
        action="store_true",
        help="Explicitly allow a production LAN gateway TCP connection.",
    )
    parser.add_argument(
        "--host-env",
        default=DEFAULT_HOST_ENV,
        help=(
            "Environment variable containing the LAN gateway host. "
            f"Default: {DEFAULT_HOST_ENV}"
        ),
    )
    parser.add_argument(
        "--port-env",
        default=DEFAULT_PORT_ENV,
        help=(
            "Optional environment variable containing the LAN gateway TCP port. "
            f"Default: {DEFAULT_PORT_ENV}; fallback: {DEFAULT_PORT}"
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help=f"Maximum probe timeout, capped at {int(MAX_TIMEOUT_SECONDS)} seconds.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=5,
        help=f"Maximum received LAN frames, capped at {MAX_FRAMES}.",
    )
    return parser


def validate_run_request(
    args: argparse.Namespace,
    environ: Mapping[str, str],
) -> RunSafety:
    """Fail closed unless the user explicitly enables production LAN networking."""
    if not args.confirm_production_lan_gateway:
        return RunSafety(False, error="missing_confirm_flag")

    host = str(environ.get(str(args.host_env).strip(), "")).strip()
    if not host:
        return RunSafety(False, error="missing_host_env")

    port = _port_from_env(args.port_env, environ)
    if port is None:
        return RunSafety(False, error="invalid_port_env")

    timeout = float(args.timeout_seconds)
    if timeout <= 0 or timeout > MAX_TIMEOUT_SECONDS:
        return RunSafety(False, error="invalid_timeout")

    max_frames = int(args.max_frames)
    if max_frames <= 0 or max_frames > MAX_FRAMES:
        return RunSafety(False, error="invalid_max_frames")

    return RunSafety(
        True,
        host=host,
        port=port,
        timeout_seconds=timeout,
        max_frames=max_frames,
    )


async def async_probe_lan_gateway(
    *,
    host: str,
    port: int,
    timeout_seconds: float,
    max_frames: int,
) -> LanGatewayProbeSummary:
    """Open one LAN TCP connection and read aggregate gateway frame facts."""
    summary = LanGatewayProbeSummary(network_attempted=True)
    writer: Any | None = None
    try:
        async with asyncio.timeout(timeout_seconds):
            reader, writer = await asyncio.open_connection(host, port)
            summary.connected = True
            writer.write(_encode_topology_request())
            await writer.drain()
            summary.sent_topology_request = True
            await _read_lan_frames(reader, summary, max_frames=max_frames)
        summary.ok = summary.connected and summary.sent_topology_request and summary.frames_seen > 0
    except TimeoutError:
        summary.last_error_type = "TimeoutError"
        summary.ok = False
    except Exception as err:  # pragma: no cover - production network boundary
        summary.last_error_type = type(err).__name__
        summary.ok = False
    finally:
        if writer is not None:
            writer.close()
            wait_closed = getattr(writer, "wait_closed", None)
            if callable(wait_closed):
                await wait_closed()
    return summary


async def _read_lan_frames(
    reader: Any,
    summary: LanGatewayProbeSummary,
    *,
    max_frames: int,
) -> None:
    """Read CRLF-delimited LAN frames and keep only aggregate facts."""
    buffer = ""
    while summary.frames_seen < max_frames:
        data = await reader.read(4096)
        if not data:
            return
        buffer += data.decode("utf-8")
        if LAN_FRAME_SEPARATOR not in buffer:
            continue
        parts = buffer.split(LAN_FRAME_SEPARATOR)
        buffer = parts.pop()
        for raw_frame in parts:
            if summary.frames_seen >= max_frames:
                return
            _update_summary_from_raw_frame(summary, raw_frame)


def _update_summary_from_raw_frame(
    summary: LanGatewayProbeSummary,
    raw_frame: str,
) -> None:
    """Classify one raw LAN frame without retaining payload values."""
    try:
        payload = json.loads(raw_frame)
    except json.JSONDecodeError:
        summary.parse_error_frames += 1
        return
    if not isinstance(payload, Mapping):
        summary.parse_error_frames += 1
        return
    _update_summary_from_payload(summary, payload)


def _update_summary_from_payload(
    summary: LanGatewayProbeSummary,
    payload: Mapping[str, Any],
) -> None:
    """Classify one LAN JSON object without copying payload values."""
    method = str(payload.get("method", "")).strip()
    summary.frames_seen += 1
    if method:
        summary.methods[method] += 1
    if method == "gateway_post.topology":
        summary.topology_frames += 1
    elif method == "gateway_post.prop":
        summary.property_frames += 1
    elif method == "gateway_post.event":
        summary.event_frames += 1
    else:
        summary.other_json_frames += 1


def _encode_topology_request() -> bytes:
    """Encode one documented topology request frame."""
    payload = {
        "version": "1.0",
        "id": 1,
        "method": METHOD_GET_TOPOLOGY,
    }
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + LAN_FRAME_SEPARATOR
    ).encode("utf-8")


def _port_from_env(name: str, environ: Mapping[str, str]) -> int | None:
    """Return a valid TCP port from the configured environment variable."""
    raw_port = str(environ.get(str(name).strip(), "")).strip()
    if not raw_port:
        return DEFAULT_PORT
    try:
        port = int(raw_port)
    except ValueError:
        return None
    return port if 0 < port <= 65535 else None


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
        async_probe_lan_gateway(
            host=safety.host,
            port=safety.port,
            timeout_seconds=safety.timeout_seconds,
            max_frames=safety.max_frames,
        )
    )
    result = summary.as_dict()
    print(json.dumps(result, sort_keys=True))
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
