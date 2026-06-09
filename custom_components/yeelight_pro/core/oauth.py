"""Yeelight OAuth token endpoint runtime helpers."""

from __future__ import annotations

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from ..oauth_contract import (
    DEFAULT_OAUTH_TOKEN_URL,
    YeelightOAuthToken,
    build_authorization_code_token_body,
    build_refresh_token_body,
    parse_oauth_token_response,
    raise_for_oauth_error,
)
from .exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    RateLimitError,
    ServerError,
    safe_error_summary,
)

_OAUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}


async def request_oauth_token(
    session: ClientSession,
    timeout: ClientTimeout,
    body: dict[str, str],
) -> YeelightOAuthToken:
    """Send a documented OAuth token request without leaking raw responses."""
    try:
        async with session.post(
            DEFAULT_OAUTH_TOKEN_URL,
            data=body,
            headers=_OAUTH_HEADERS,
            timeout=timeout,
        ) as response:
            if response.status == 401:
                raise AuthenticationError("Yeelight OAuth authorization failed")
            if response.status == 403:
                raise AuthenticationError("Yeelight OAuth authorization denied")
            if response.status == 429:
                raise RateLimitError("Rate limit exceeded")
            if response.status >= 500:
                raise ServerError(f"Server error: HTTP {response.status}")

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

            if response.status >= 400:
                raise_for_oauth_error(payload)
                raise CommandError(f"OAuth HTTP {response.status} request failed")

            return parse_oauth_token_response(payload)
    except aiohttp.ClientError as err:
        raise ConnectionError(
            f"OAuth connection error: {safe_error_summary(err)}"
        ) from None


async def exchange_authorization_code(
    session: ClientSession,
    timeout: ClientTimeout,
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    device: str | None = "home-assistant",
) -> YeelightOAuthToken:
    """Exchange an OAuth authorization code for Yeelight access tokens."""
    return await request_oauth_token(
        session,
        timeout,
        build_authorization_code_token_body(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            code=code,
            device=device,
        ),
    )


async def refresh_oauth_token(
    session: ClientSession,
    timeout: ClientTimeout,
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> YeelightOAuthToken:
    """Refresh Yeelight OAuth tokens with the documented single-use token."""
    return await request_oauth_token(
        session,
        timeout,
        build_refresh_token_body(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        ),
    )


__all__ = [
    "exchange_authorization_code",
    "refresh_oauth_token",
    "request_oauth_token",
]
