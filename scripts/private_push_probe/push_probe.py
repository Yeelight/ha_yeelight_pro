"""WebSocket collection for the private push topology probe."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import time
from typing import Any

import aiohttp
from aiohttp import WSMsgType

from custom_components.yeelight_pro.push import (  # noqa: E402
    ATTR_NODE_ID_CANDIDATES,
    push_event_payloads,
    push_property_updates,
)
from custom_components.yeelight_pro.push_contract import (  # noqa: E402
    PUSH_CONTROL_METHODS,
    PUSH_HEARTBEAT_INTERVAL_SECONDS,
    PushMessageBuilder,
    build_push_url,
)
from custom_components.yeelight_pro.push_transport_frames import (  # noqa: E402
    control_frame_subscribe_node_candidate_hash_samples,
    data_frame_node_candidate_hash_samples,
    is_control_frame,
    is_push_data_payload,
    json_payload_from_message,
    payload_type,
    private_status_reason_label,
    private_status_result_label,
)
from custom_components.yeelight_pro.push_transport_private_frames import (  # noqa: E402
    private_subscribe_state_payload,
)

from scripts.private_push_probe.matching import (
    classify_node_candidates,
    record_hash_group_match,
)
from scripts.private_push_probe.models import ProbeSummary, TopologySnapshot
from scripts.private_push_probe.snapshot import (
    subscribe_snapshot_samples,
    subscribe_snapshot_summary,
    subscribe_topology_coverage,
    unsafe_subscribe_snapshot_details,
)
from scripts.private_push_probe.topology import (
    classify_update,
)

MAX_SAMPLES = 12


async def probe_push(
    *,
    session: aiohttp.ClientSession,
    token: str,
    push_base_url: str,
    topology: TopologySnapshot,
    duration_seconds: float,
    max_frames: int,
    unsafe_local_details: bool = False,
) -> ProbeSummary:
    """Subscribe to push and compare received payload ids with topology."""
    summary = ProbeSummary()
    builder = PushMessageBuilder()
    heartbeat_task: asyncio.Task[None] | None = None
    deadline = time.monotonic() + duration_seconds
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
                await handle_message(
                    summary,
                    topology,
                    message,
                    unsafe_local_details=unsafe_local_details,
                )
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
    return summary


async def handle_message(
    summary: ProbeSummary,
    topology: TopologySnapshot,
    message: Any,
    *,
    unsafe_local_details: bool = False,
) -> None:
    """Classify one websocket message."""
    if message.type not in {WSMsgType.TEXT, WSMsgType.BINARY}:
        return
    summary.frames_seen += 1
    payload = json_payload_from_message(message)
    if payload is None:
        summary.malformed_frames += 1
        return
    payload_type_value = payload_type(payload)
    if payload_type_value:
        summary.payload_types[payload_type_value] += 1
    if is_control_frame(payload):
        record_control_frame(
            summary,
            topology,
            payload,
            unsafe_local_details=unsafe_local_details,
        )
    snapshot_payload = private_subscribe_state_payload(payload)
    if snapshot_payload is not None:
        record_data_payload(summary, topology, snapshot_payload)
        return
    if not is_push_data_payload(payload):
        if not is_control_frame(payload):
            summary.unsupported_frames += 1
        return
    record_data_payload(summary, topology, payload)


def record_data_payload(
    summary: ProbeSummary,
    topology: TopologySnapshot,
    payload: Mapping[str, Any],
) -> None:
    """Record one data payload using the same push parser as runtime."""
    summary.data_frames += 1
    record_hash_group_match(
        summary.data_hash_match,
        data_frame_node_candidate_hash_samples(payload),
        topology,
    )
    record_property_updates(summary, topology, payload)
    record_event_payloads(summary, topology, payload)


def record_control_frame(
    summary: ProbeSummary,
    topology: TopologySnapshot,
    payload: Mapping[str, Any],
    *,
    unsafe_local_details: bool = False,
) -> None:
    """Record aggregate control-frame diagnostics."""
    summary.control_frames += 1
    method = str(payload.get("method") or "result")
    if method in PUSH_CONTROL_METHODS or method == "result":
        summary.control_methods[method] += 1
    if private_status_result_label(payload) == "non_success":
        summary.private_status_non_success_frames += 1
        reason = private_status_reason_label(payload)
        if reason is not None:
            summary.last_private_status_reason = reason
    record_hash_group_match(
        summary.subscribe_match,
        control_frame_subscribe_node_candidate_hash_samples(payload),
        topology,
    )
    snapshot_summary = subscribe_snapshot_summary(payload, topology)
    if snapshot_summary:
        summary.subscribe_snapshot_summary = snapshot_summary
    snapshot_samples = subscribe_snapshot_samples(payload, topology)
    if snapshot_samples:
        summary.subscribe_topology_coverage = subscribe_topology_coverage(
            snapshot_samples,
            topology,
            unsafe_local_details=unsafe_local_details,
        )
    for sample in snapshot_samples:
        if len(summary.subscribe_samples) >= MAX_SAMPLES:
            break
        summary.subscribe_samples.append(sample)
    if unsafe_local_details:
        for detail in unsafe_subscribe_snapshot_details(payload, topology):
            if len(summary.unsafe_subscribe_details) >= MAX_SAMPLES:
                break
            summary.unsafe_subscribe_details.append(detail)


def record_property_updates(
    summary: ProbeSummary,
    topology: TopologySnapshot,
    payload: Mapping[str, Any],
) -> None:
    """Add topology matching facts for parsed property updates."""
    for update in push_property_updates(payload):
        summary.prop_updates += 1
        if not update.params:
            summary.empty_param_updates += 1
        match = classify_update(update, topology)
        summary.matched_loaded_topology += int(match["matched"])
        summary.selected_id_loaded += int(match["selected_loaded"])
        summary.alias_resolved_matches += int(match["alias_resolved"])
        summary.not_loaded += int(match["not_loaded"])
        summary.maybe_filtered += int(match["maybe_filtered"])
        summary.ambiguous_candidates += int(match["ambiguous"])
        if len(summary.update_samples) < MAX_SAMPLES:
            summary.update_samples.append(match["sample"])


def record_event_payloads(
    summary: ProbeSummary,
    topology: TopologySnapshot,
    payload: Mapping[str, Any],
) -> None:
    """Add topology matching facts for parsed event payloads."""
    for event_payload in push_event_payloads(payload):
        summary.event_payloads += 1
        source_id = _to_int(event_payload.get("source_device_id"))
        if source_id is None:
            summary.event_not_loaded += 1
            continue
        node_type = None
        attributes = event_payload.get("event_attributes")
        if isinstance(attributes, Mapping):
            node_type = _to_int(attributes.get("node_type"))
        candidates = _event_node_id_candidates(event_payload, source_id)
        match = classify_node_candidates(
            topology=topology,
            node_id=source_id,
            node_type=node_type,
            params={},
            node_id_candidates=candidates,
        )
        summary.event_matched_loaded_topology += int(match["matched"])
        summary.event_selected_id_loaded += int(match["selected_loaded"])
        summary.event_alias_resolved_matches += int(match["alias_resolved"])
        summary.event_not_loaded += int(match["not_loaded"])
        summary.event_maybe_filtered += int(match["maybe_filtered"])
        summary.event_ambiguous_candidates += int(match["ambiguous"])
        if len(summary.event_samples) < MAX_SAMPLES:
            sample = dict(match["sample"])
            sample["event_type"] = str(event_payload.get("event_type") or "")
            summary.event_samples.append(sample)


def _event_node_id_candidates(
    event_payload: Mapping[str, Any],
    source_id: int,
) -> tuple[tuple[str, int], ...]:
    """Return event candidate ids in the same shape as property updates."""
    raw_candidates = event_payload.get(ATTR_NODE_ID_CANDIDATES)
    if not isinstance(raw_candidates, tuple):
        return (("source_device_id", source_id),)
    candidates: list[tuple[str, int]] = []
    for item in raw_candidates:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], int)
        ):
            continue
        candidates.append((item[0], item[1]))
    return tuple(candidates) or (("source_device_id", source_id),)


def _to_int(value: Any) -> int | None:
    """Return an int for ordinary numeric payload values."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def send_heartbeats(
    ws: Any,
    builder: PushMessageBuilder,
    summary: ProbeSummary,
) -> None:
    """Send documented heartbeat frames while the probe is active."""
    while True:
        await asyncio.sleep(PUSH_HEARTBEAT_INTERVAL_SECONDS)
        await ws.send_json(builder.next_heartbeat())
        summary.heartbeats_sent += 1
