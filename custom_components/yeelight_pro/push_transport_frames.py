"""Frame parsing helpers for Yeelight Pro WebSocket push transport."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from aiohttp import WSMsgType

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


def is_push_data_payload(payload: dict[str, Any]) -> bool:
    """Return whether a WebSocket object is a documented prop/event payload."""
    if _is_data_payload_object(payload):
        return True
    for key in ("data", "params", "result"):
        nested = payload.get(key)
        if isinstance(nested, Mapping) and _is_data_payload_object(nested):
            return True
    return False


def payload_type(payload: Mapping[str, Any]) -> str | None:
    """Return the documented prop/event type without exposing raw payload data."""
    value = payload.get("type")
    if isinstance(value, str) and value:
        return value
    for key in ("data", "params", "result"):
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            nested_type = nested.get("type")
            if isinstance(nested_type, str) and nested_type:
                return nested_type
    return None


def is_control_frame(payload: Mapping[str, Any]) -> bool:
    """Return whether the frame is a subscribe/heartbeat control response."""
    return payload.get("method") in PUSH_CONTROL_METHODS or is_result_control_payload(
        payload
    )


def raise_for_control_error_frame(payload: dict[str, Any]) -> None:
    """Reject control errors without exposing vendor text or payload values."""
    method = payload.get("method")
    if method not in PUSH_CONTROL_METHODS and not is_result_control_payload(payload):
        return
    if is_control_error_payload(payload):
        raise PushControlFrameError


def _is_data_payload_object(payload: Mapping[str, Any]) -> bool:
    """Return whether an object is a push data frame adapter can consume."""
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


def is_result_control_payload(payload: Mapping[str, Any]) -> bool:
    """Return whether a method-less result frame is a production control ACK."""
    if "type" in payload or "result" not in payload:
        return False
    result = payload.get("result")
    return isinstance(result, bool) or isinstance(result, Mapping)


def is_control_error_payload(payload: Mapping[str, Any]) -> bool:
    """Classify control errors using aggregate-safe success/code markers."""
    success = payload.get("success")
    code = str(payload.get("code", "")).strip()
    result = payload.get("result")
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
