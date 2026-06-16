"""Yeelight account scan-login runtime helpers."""

from __future__ import annotations

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from ..scan_login_contract import (
    ScanLoginStatus,
    YeelightScanLoginQrCode,
    account_base_url,
    build_scan_login_qrcode_path,
    build_scan_login_status_path,
    parse_scan_login_response,
)
from .exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    RateLimitError,
    ServerError,
    safe_error_summary,
)

_SCAN_LOGIN_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}


async def request_scan_login_state(
    session: ClientSession,
    timeout: ClientTimeout,
    *,
    region: str,
    path: str,
    base_url: str | None = None,
) -> YeelightScanLoginQrCode:
    """Send one scan-login request without leaking QR code or token payloads."""
    endpoint = (base_url or account_base_url(region)).rstrip("/")
    try:
        async with session.post(
            f"{endpoint}{path}",
            data={},
            headers=_SCAN_LOGIN_HEADERS,
            timeout=timeout,
        ) as response:
            if response.status in (401, 403):
                raise AuthenticationError("Yeelight scan-login authorization failed")
            if response.status == 429:
                raise RateLimitError("Rate limit exceeded")
            if response.status >= 500:
                raise ServerError(f"Server error: HTTP {response.status}")
            if response.status >= 400:
                raise CommandError(f"Scan-login HTTP {response.status} request failed")

            try:
                payload = await response.json()
            except (aiohttp.ContentTypeError, ValueError) as err:
                raise ConnectionError(
                    f"Invalid scan-login JSON response: {safe_error_summary(err)}"
                ) from None
            if not isinstance(payload, dict):
                raise ConnectionError(
                    f"Unexpected scan-login JSON response type: "
                    f"{type(payload).__name__}"
                )
            return parse_scan_login_response(payload)
    except aiohttp.ClientError as err:
        raise ConnectionError(
            f"Scan-login connection error: {safe_error_summary(err)}"
        ) from None


async def create_scan_login_qrcode(
    session: ClientSession,
    timeout: ClientTimeout,
    *,
    region: str,
    device: str,
    base_url: str | None = None,
) -> YeelightScanLoginQrCode:
    """Create a 5-minute Yeelight APP scan-login QR code state."""
    return await request_scan_login_state(
        session,
        timeout,
        region=region,
        path=build_scan_login_qrcode_path(device),
        base_url=base_url,
    )


async def check_scan_login_qrcode(
    session: ClientSession,
    timeout: ClientTimeout,
    *,
    region: str,
    qr_code_id: str,
    base_url: str | None = None,
) -> YeelightScanLoginQrCode:
    """Poll a Yeelight APP scan-login QR code state."""
    return await request_scan_login_state(
        session,
        timeout,
        region=region,
        path=build_scan_login_status_path(qr_code_id),
        base_url=base_url,
    )


__all__ = [
    "ScanLoginStatus",
    "YeelightScanLoginQrCode",
    "check_scan_login_qrcode",
    "create_scan_login_qrcode",
    "request_scan_login_state",
]
