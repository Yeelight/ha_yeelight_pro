"""HTTP request helpers for Yeelight Pro client."""
from __future__ import annotations

from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from .exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    RateLimitError,
    ServerError,
    TokenExpiredError,
    safe_error_summary,
)
from .http_errors import raise_for_body_error


def build_client_headers(
    *,
    access_token: str,
    client_id: str,
    with_auth: bool = True,
) -> dict[str, str]:
    """Build Open API request headers."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if with_auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if client_id:
        headers["clientId"] = client_id
    return headers


async def request_json(
    session: ClientSession,
    timeout: ClientTimeout,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    **kwargs: Any,
) -> dict[str, Any]:
    """Send one Open API request and return a validated JSON object."""
    try:
        async with session.request(
            method,
            url,
            headers=headers,
            timeout=timeout,
            **kwargs,
        ) as response:
            if response.status == 401:
                raise TokenExpiredError("Access token expired or invalid")
            if response.status == 403:
                raise AuthenticationError("Access denied")
            if response.status == 429:
                raise RateLimitError("Rate limit exceeded")
            if response.status >= 500:
                raise ServerError(f"Server error: HTTP {response.status}")
            if response.status >= 400:
                raise CommandError(f"HTTP {response.status} request failed")

            try:
                payload = await response.json()
            except (aiohttp.ContentTypeError, ValueError) as err:
                raise ConnectionError(
                    f"Invalid JSON response: {safe_error_summary(err)}"
                ) from None

            if not isinstance(payload, dict):
                raise ConnectionError(
                    f"Unexpected JSON response type: {type(payload).__name__}"
                )

            raise_for_body_error(payload)
            return payload
    except aiohttp.ClientError as err:
        raise ConnectionError(
            f"Connection error: {safe_error_summary(err)}"
        ) from None
