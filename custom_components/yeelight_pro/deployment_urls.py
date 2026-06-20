"""Deployment URL helpers for cloud and private Yeelight endpoints."""
from __future__ import annotations

from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit, urlunsplit

IOT_API_SUFFIX = "/apis/iot"
ACCOUNT_API_SUFFIX = "/apis/account"
PUSH_WS_SUFFIX = "/ws"
_API_SUFFIXES = (IOT_API_SUFFIX, ACCOUNT_API_SUFFIX, PUSH_WS_SUFFIX)
_PRIVATE_PUSH_HOST_OVERRIDES = {
    "api-dev.yeedev.com": ("ws", "192.168.1.202:7779", PUSH_WS_SUFFIX),
    "ws-dev.yeedev.com": ("ws", "192.168.1.202:7779", PUSH_WS_SUFFIX),
    "api-test.yeedev.com": ("ws", "192.168.0.89:7779", PUSH_WS_SUFFIX),
    "ws-test.yeedev.com": ("ws", "192.168.0.89:7779", PUSH_WS_SUFFIX),
}
_KNOWN_PRIVATE_PUSH_NETLOCS = frozenset(
    netloc for _scheme, netloc, _path in _PRIVATE_PUSH_HOST_OVERRIDES.values()
)


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


def deployment_private_push_base_url(
    private_domain: Any,
    private_push_domain: Any = "",
) -> str:
    """Return the effective private push URL for an API root and optional override."""
    api_push_url = deployment_push_base_url(private_domain)
    push_text = "" if private_push_domain is None else str(private_push_domain).strip()
    if not push_text:
        return api_push_url

    push_url = deployment_push_base_url(push_text)
    if _is_conflicting_known_private_push(api_push_url, push_url):
        return api_push_url
    return push_url


def _with_default_scheme(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _with_default_push_scheme(value: str) -> str:
    if value.startswith(("ws://", "wss://", "http://", "https://")):
        return value
    if _is_local_push_host(value):
        return f"ws://{value}"
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


def _is_conflicting_known_private_push(api_push_url: str, push_url: str) -> bool:
    """Return true when a known internal API host points at another lab push route."""
    api_parsed = urlsplit(api_push_url)
    push_parsed = urlsplit(push_url)
    api_netloc = api_parsed.netloc.casefold()
    push_netloc = push_parsed.netloc.casefold()
    return (
        api_netloc in _KNOWN_PRIVATE_PUSH_NETLOCS
        and push_netloc in _KNOWN_PRIVATE_PUSH_NETLOCS
        and api_netloc != push_netloc
    )


def _is_local_push_host(value: str) -> bool:
    host = value.split("/", 1)[0].rsplit(":", 1)[0].strip("[]").casefold()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ip_address(host).is_private
    except ValueError:
        return False


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
    "deployment_private_push_base_url",
    "deployment_push_base_url",
    "deployment_root_url",
]
