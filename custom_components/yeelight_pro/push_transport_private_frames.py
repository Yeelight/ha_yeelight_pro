"""Private-deployment control-frame helpers for Yeelight Pro push transport."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .push_contract import PUSH_CONTROL_METHODS
from .push_transport_frame_nodes import (
    MAX_SAFE_NODE_ID_HASH_SAMPLES,
    node_id_hash_group,
)

SNAPSHOT_STATE_CONTAINER_KEYS = ("params", "properties", "props", "data")


def private_status_result_label(payload: Mapping[str, Any]) -> str | None:
    """Return a coarse, value-safe status label for private status frames."""
    if not is_private_status_frame(payload):
        return None
    return "success" if is_private_status_ack(payload) else "non_success"


def private_status_reason_label(payload: Mapping[str, Any]) -> str | None:
    """Return a fixed diagnostics reason for known private status errors."""
    if not is_private_status_frame(payload):
        return None
    data = payload.get("data")
    message = data.get("message") if isinstance(data, Mapping) else None
    if not isinstance(message, str):
        return None
    normalized = "".join(message.strip().casefold().split())
    if "无可订阅设备" in message or "nosubscribabledevice" in normalized:
        return "no_subscribable_devices"
    return None


def private_subscribe_devices(
    payload: Mapping[str, Any],
) -> list[Mapping[str, Any]] | None:
    """Return private subscribe snapshot devices, if present."""
    if not is_private_subscribe_snapshot(payload):
        return None
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None
    devices = data.get("devices")
    if not isinstance(devices, list):
        return None
    return [device for device in devices if isinstance(device, Mapping)]


def private_subscribe_state_payload(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return a prop payload for state rows carried by private subscribe snapshots."""
    devices = private_subscribe_devices(payload)
    if devices is None:
        return None
    nodes = [dict(device) for device in devices if snapshot_state_keys(device)]
    if not nodes:
        return None
    return {"type": "prop", "nodes": nodes}


def subscribe_snapshot_node_candidate_hash_samples(
    payload: Mapping[str, Any],
) -> list[list[str]]:
    """Return redacted subscribe node-id alias hash groups."""
    devices = private_subscribe_devices(payload)
    if devices is None:
        return []
    samples: list[list[str]] = []
    for device in devices:
        group = node_id_hash_group(device)
        if not group:
            continue
        if group not in samples:
            samples.append(group)
        if len(samples) >= MAX_SAFE_NODE_ID_HASH_SAMPLES:
            break
    return samples


def snapshot_state_keys(device: Mapping[str, Any]) -> list[str]:
    """Return state-like field names from a subscribe snapshot device."""
    keys: list[str] = []
    for key in SNAPSHOT_STATE_CONTAINER_KEYS:
        value = device.get(key)
        if isinstance(value, Mapping) and value:
            keys.append(key)
        elif isinstance(value, list) and value:
            keys.append(key)
    if "o" in device:
        keys.append("o")
    prop_id = device.get("propId") or device.get("propName")
    if prop_id not in (None, "") and "value" in device:
        keys.extend(key for key in ("propId", "propName", "value") if key in device)
    return keys


def is_private_status_ack(payload: Mapping[str, Any]) -> bool:
    """Return true for method-less private success ACKs with status text only."""
    if not is_private_status_frame(payload):
        return False
    result = payload.get("result")
    return isinstance(result, str) and result.strip().casefold() in {"ok", "success"}


def is_private_status_frame(payload: Mapping[str, Any]) -> bool:
    """Return true for method-less private status frames without data fields."""
    if payload.get("method") not in (None, ""):
        return False
    if "type" in payload or "result" not in payload:
        return False
    result = payload.get("result")
    if not isinstance(result, str):
        return False
    data = payload.get("data")
    if data is None:
        return True
    if not isinstance(data, Mapping):
        return False
    return not any(
        key in data
        for key in (
            "method",
            "type",
            "nodes",
            "params",
            "properties",
            "props",
            "propId",
            "propName",
        )
    )


def is_private_subscribe_snapshot(payload: Mapping[str, Any]) -> bool:
    """Return true for private deployments that echo subscribe metadata."""
    if payload.get("method") not in (None, ""):
        return False
    if "type" in payload or "result" not in payload:
        return False
    result = payload.get("result")
    if isinstance(result, str) and result.casefold() != "ok":
        return False
    if not isinstance(result, (str, bool)):
        return False
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return isinstance(result, str)
    return data.get("method") in PUSH_CONTROL_METHODS


__all__ = [
    "is_private_status_ack",
    "is_private_status_frame",
    "is_private_subscribe_snapshot",
    "private_status_reason_label",
    "private_status_result_label",
    "private_subscribe_devices",
    "private_subscribe_state_payload",
    "snapshot_state_keys",
    "subscribe_snapshot_node_candidate_hash_samples",
]
