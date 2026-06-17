"""Yeelight Open API OAuth token refresh helpers."""

from __future__ import annotations

from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from ..scan_login_contract import YeelightAccountToken, account_base_url, parse_account_token
from .exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    RateLimitError,
    ServerError,
    safe_error_summary,
)
from .http_errors import raise_for_body_error

_OAUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}


async def refresh_access_token(
    session: ClientSession,
    timeout: ClientTimeout,
    *,
    region: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    base_url: str | None = None,
    allow_empty_client_secret: bool = False,
) -> YeelightAccountToken:
    """Refresh an OAuth access token using the documented account API."""
    client_secret_value = _optional_text(client_secret)
    data = {
        "grant_type": "refresh_token",
        "client_id": _required_text(client_id, "client_id"),
        "refresh_token": _required_text(refresh_token, "refresh_token"),
    }
    if client_secret_value or not allow_empty_client_secret:
        data["client_secret"] = (
            client_secret_value
            if allow_empty_client_secret
            else _required_text(client_secret, "client_secret")
        )
    endpoint = (base_url or account_base_url(region)).rstrip("/")
    try:
        async with session.post(
            f"{endpoint}/oauth/token",
            data=data,
            headers=_OAUTH_HEADERS,
            timeout=timeout,
        ) as response:
            if response.status in (400, 401, 403):
                raise AuthenticationError("Yeelight OAuth token refresh failed")
            if response.status == 429:
                raise RateLimitError("Rate limit exceeded")
            if response.status >= 500:
                raise ServerError(f"Server error: HTTP {response.status}")
            if response.status >= 400:
                raise CommandError(f"OAuth HTTP {response.status} request failed")

            try:
                payload = await response.json()
            except (aiohttp.ContentTypeError, ValueError) as err:
                raise ConnectionError(
                    f"Invalid OAuth JSON response: {safe_error_summary(err)}"
                ) from None
            if not isinstance(payload, dict):
                raise ConnectionError(
                    f"Unexpected OAuth JSON response type: {type(payload).__name__}"
                )
            raise_for_body_error(payload)
            return parse_account_token(payload)
    except aiohttp.ClientError as err:
        raise ConnectionError(
            f"OAuth connection error: {safe_error_summary(err)}"
        ) from None


def _required_text(value: Any, field: str) -> str:
    """Return required text without exposing the raw OAuth value."""
    if not isinstance(value, str) or not value.strip():
        raise AuthenticationError(f"Yeelight OAuth {field} is required")
    return value.strip()


def _optional_text(value: Any) -> str:
    """Return optional OAuth text without exposing the raw value."""
    return value.strip() if isinstance(value, str) else ""


__all__ = ["refresh_access_token"]
