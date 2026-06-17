"""Deployment URL helpers for cloud and private Yeelight endpoints."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

IOT_API_SUFFIX = "/apis/iot"
ACCOUNT_API_SUFFIX = "/apis/account"
PUSH_WS_SUFFIX = "/ws"
_API_SUFFIXES = (IOT_API_SUFFIX, ACCOUNT_API_SUFFIX, PUSH_WS_SUFFIX)
_PRIVATE_PUSH_HOST_OVERRIDES = {
    "api-test.yeedev.com": ("ws", "ws-test.yeedev.com", PUSH_WS_SUFFIX),
    "ws-test.yeedev.com": ("ws", "ws-test.yeedev.com", PUSH_WS_SUFFIX),
}


def deployment_root_url(value: Any) -> str:
    """Return the deployment root URL, accepting legacy API-prefix entries."""
    root = _with_default_scheme(_required_text(value)).rstrip("/")
    lowered = root.lower()
    for suffix in _API_SUFFIXES:
        if lowered.endswith(suffix):
            return root[: -len(suffix)].rstrip("/")
    return root


def deployment_iot_base_url(value: Any) -> str:
    """Return the IoT Open API base URL for a deployment root or legacy prefix."""
    return f"{deployment_root_url(value)}{IOT_API_SUFFIX}"


def deployment_account_base_url(value: Any) -> str:
    """Return the Account API base URL for a deployment root or legacy prefix."""
    return f"{deployment_root_url(value)}{ACCOUNT_API_SUFFIX}"


def deployment_push_base_url(value: Any) -> str:
    """Return the WebSocket push base URL for a deployment root or push host."""
    root = _with_default_push_scheme(_required_text(value)).rstrip("/")
    lowered = root.lower()
    for suffix in _API_SUFFIXES:
        if lowered.endswith(suffix):
            root = root[: -len(suffix)].rstrip("/")
            break
    if override := _private_push_host_override(root):
        return override
    return f"{_http_to_ws(root)}{PUSH_WS_SUFFIX}"


def _with_default_scheme(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _with_default_push_scheme(value: str) -> str:
    if value.startswith(("ws://", "wss://", "http://", "https://")):
        return value
    return f"wss://{value}"


def _http_to_ws(value: str) -> str:
    if value.startswith(("ws://", "wss://")):
        return value
    if value.startswith("https://"):
        return f"wss://{value[len('https://'):]}"
    if value.startswith("http://"):
        return f"ws://{value[len('http://'):]}"
    return value


def _private_push_host_override(value: str) -> str | None:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").casefold()
    if host not in _PRIVATE_PUSH_HOST_OVERRIDES:
        return None
    scheme, netloc, path = _PRIVATE_PUSH_HOST_OVERRIDES[host]
    return urlunsplit((scheme, netloc, path, "", ""))


def _required_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Yeelight deployment URL is required")
    return value.strip()


__all__ = [
    "ACCOUNT_API_SUFFIX",
    "IOT_API_SUFFIX",
    "PUSH_WS_SUFFIX",
    "deployment_account_base_url",
    "deployment_iot_base_url",
    "deployment_push_base_url",
    "deployment_root_url",
]
