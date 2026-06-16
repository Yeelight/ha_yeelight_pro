"""Deployment URL helpers for cloud and private Yeelight endpoints."""
from __future__ import annotations

from typing import Any

IOT_API_SUFFIX = "/apis/iot"
ACCOUNT_API_SUFFIX = "/apis/account"
_API_SUFFIXES = (IOT_API_SUFFIX, ACCOUNT_API_SUFFIX)


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


def _with_default_scheme(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _required_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Yeelight deployment URL is required")
    return value.strip()


__all__ = [
    "ACCOUNT_API_SUFFIX",
    "IOT_API_SUFFIX",
    "deployment_account_base_url",
    "deployment_iot_base_url",
    "deployment_root_url",
]
