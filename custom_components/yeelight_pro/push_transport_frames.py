"""Frame parsing helpers for Yeelight Pro WebSocket push transport."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from aiohttp import WSMsgType

from .lan_methods import (
    METHOD_DEVICE_POST_EVENT,
    METHOD_DEVICE_POST_PROP,
    METHOD_POST_EVENT,
    METHOD_POST_PROP,
)
from .push_contract import PUSH_CONTROL_METHODS, PUSH_DATA_TYPES


class PushControlFrameError(Exception):
    """Aggregate-only error for failed WebSocket control frames."""


def json_payload_from_message(message: Any) -> dict[str, Any] | None:
    """Return a JSON object payload for text/json websocket messages."""
    message_type = getattr(message, "type", None)
    if message_type not in {WSMsgType.TEXT, WSMsgType.BINARY}:
        return None

    data = getattr(message, "data", None)
    if isinstance(data, bytes):
        try:
            data = data.decode()
        except UnicodeDecodeError:
            return None
    if not isinstance(data, str):
        return None

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


_MAX_NESTED_PAYLOAD_DEPTH = 4


def is_push_data_payload(payload: dict[str, Any]) -> bool:
    """Return whether a WebSocket object is a documented prop/event payload."""
    for candidate in _iter_payload_candidates(payload):
        if _is_data_payload_object(candidate):
            return True
    return False


def payload_type(payload: Mapping[str, Any]) -> str | None:
    """Return the documented prop/event type without exposing raw payload data."""
    for candidate in _iter_payload_candidates(payload):
        value = candidate.get("type")
        if isinstance(value, str) and value:
            return value
        method = candidate.get("method")
        if isinstance(method, str) and method in _PUSH_COMPAT_DATA_METHODS:
            return method
    return None


def _iter_payload_candidates(
    payload: Mapping[str, Any],
    *,
    depth: int = 0,
) -> list[Mapping[str, Any]]:
    """Return nested payload objects that private gateways may wrap repeatedly."""
    candidates = [payload]
    if depth >= _MAX_NESTED_PAYLOAD_DEPTH:
        return candidates
    for key in ("data", "params", "result"):
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            candidates.extend(_iter_payload_candidates(nested, depth=depth + 1))
    return candidates


def is_control_frame(payload: Mapping[str, Any]) -> bool:
    """Return whether the frame is a subscribe/heartbeat control response."""
    return (
        payload.get("method") in PUSH_CONTROL_METHODS
        or is_result_control_payload(payload)
        or _is_private_subscribe_snapshot(payload)
    )


def raise_for_control_error_frame(payload: dict[str, Any]) -> None:
    """Reject control errors without exposing vendor text or payload values."""
    method = payload.get("method")
    if (
        method not in PUSH_CONTROL_METHODS
        and not is_result_control_payload(payload)
        and not _is_private_subscribe_snapshot(payload)
    ):
        return
    if is_control_error_payload(payload):
        raise PushControlFrameError


def _is_data_payload_object(payload: Mapping[str, Any]) -> bool:
    """Return whether an object is a push data frame adapter can consume."""
    if _is_compat_method_payload_object(payload):
        return True
    data_type = payload.get("type")
    if data_type not in PUSH_DATA_TYPES:
        return False
    if "nodes" in payload:
        return True
    if data_type == "event" and "event" in payload:
        return True
    return any(
        key in payload
        for key in (
            "params",
            "properties",
            "props",
            "propId",
            "propName",
            "data",
        )
    )


_PUSH_COMPAT_DATA_METHODS = frozenset(
    {
        METHOD_POST_PROP,
        METHOD_DEVICE_POST_PROP,
        METHOD_POST_EVENT,
        METHOD_DEVICE_POST_EVENT,
    }
)


def _is_compat_method_payload_object(payload: Mapping[str, Any]) -> bool:
    """Return true for private deployments reusing documented LAN post frames."""
    method = payload.get("method")
    if method in {METHOD_POST_PROP, METHOD_DEVICE_POST_PROP}:
        return "nodes" in payload
    if method == METHOD_POST_EVENT:
        return "nodes" in payload
    if method == METHOD_DEVICE_POST_EVENT:
        return isinstance(payload.get("params"), Mapping)
    return False


def is_result_control_payload(payload: Mapping[str, Any]) -> bool:
    """Return whether a method-less result frame is a production control ACK."""
    if payload.get("method") not in (None, ""):
        return False
    if "type" in payload or "result" not in payload:
        return False
    result = payload.get("result")
    return isinstance(result, bool) or isinstance(result, Mapping)


def _is_private_subscribe_snapshot(payload: Mapping[str, Any]) -> bool:
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


def is_control_error_payload(payload: Mapping[str, Any]) -> bool:
    """Classify control errors using aggregate-safe success/code markers."""
    success = payload.get("success")
    code = str(payload.get("code", "")).strip()
    result = payload.get("result")
    if isinstance(result, str):
        return result.strip().casefold() not in {"ok", "success"}
    if success is False or code not in ("", "200"):
        return True
    if result is False:
        return True
    if isinstance(result, Mapping):
        result_success = result.get("success")
        result_code = str(result.get("code", "")).strip()
        return result_success is False or result_code not in ("", "200")
    return False


__all__ = [
    "PushControlFrameError",
    "is_control_error_payload",
    "is_control_frame",
    "is_push_data_payload",
    "is_result_control_payload",
    "json_payload_from_message",
    "payload_type",
    "raise_for_control_error_frame",
]
