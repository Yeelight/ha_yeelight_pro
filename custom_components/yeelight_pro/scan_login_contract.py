"""No-network scan-login contract helpers for Yeelight account APIs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import time
from typing import Any
from urllib.parse import quote

from .const import (
    CLOUD_REGION_BASE_DOMAINS,
    CLOUD_REGION_EU,
    CLOUD_REGION_SG,
    CLOUD_REGION_US,
    DEFAULT_CLOUD_REGION,
)
from .core.exceptions import ProtocolError
from .core.http_errors import raise_for_body_error
from .oauth_contract import YeelightOAuthToken, parse_oauth_token_response

SCAN_LOGIN_STATUS_CREATED = "CREATED"
SCAN_LOGIN_STATUS_SCANNED = "SCANNED"
SCAN_LOGIN_STATUS_CONFIRM = "CONFIRM"
SCAN_LOGIN_STATUS_LOGIN = "LOGIN"
SCAN_LOGIN_STATUS_EXPIRED = "EXPIRED"
SCAN_LOGIN_STATUSES = frozenset({
    SCAN_LOGIN_STATUS_CREATED,
    SCAN_LOGIN_STATUS_SCANNED,
    SCAN_LOGIN_STATUS_CONFIRM,
    SCAN_LOGIN_STATUS_LOGIN,
    SCAN_LOGIN_STATUS_EXPIRED,
})
SCAN_LOGIN_QRCODE_TTL_MS = 300_000
SCAN_LOGIN_QRCODE_TTL_SECONDS = 300
SCAN_LOGIN_SOURCE_HOME_ASSISTANT = "home-assistant"
_REGION_ALIASES = {
    "cn": DEFAULT_CLOUD_REGION,
    "china": DEFAULT_CLOUD_REGION,
    "mainland": DEFAULT_CLOUD_REGION,
    "sg": CLOUD_REGION_SG,
    "singapore": CLOUD_REGION_SG,
    "us": CLOUD_REGION_US,
    "usa": CLOUD_REGION_US,
    "na": CLOUD_REGION_US,
    "de": CLOUD_REGION_EU,
    "eu": CLOUD_REGION_EU,
    "europe": CLOUD_REGION_EU,
}


class ScanLoginStatus:
    """Scan-login status constants exposed for tests and config-flow logic."""

    CREATED = SCAN_LOGIN_STATUS_CREATED
    SCANNED = SCAN_LOGIN_STATUS_SCANNED
    CONFIRM = SCAN_LOGIN_STATUS_CONFIRM
    LOGIN = SCAN_LOGIN_STATUS_LOGIN
    EXPIRED = SCAN_LOGIN_STATUS_EXPIRED


@dataclass(frozen=True, slots=True)
class YeelightScanLoginQrCode:
    """Parsed scan-login qrcode state without raw vendor payload."""

    qr_code_id: str
    device: str
    status: str
    create_at_ms: int | None
    expire_in_ms: int | None
    expire_at_ms: int | None
    source: str
    token: YeelightOAuthToken | None

    @property
    def qrcode_content(self) -> str:
        """Return the documented qrcode content shown to the Yeelight app."""
        return build_scan_login_qrcode_content(self.qr_code_id, self.device)

    @property
    def qr_code_content(self) -> str:
        """Compatibility alias for the qrcode content."""
        return self.qrcode_content

    @property
    def expires_in_seconds(self) -> int | None:
        """Return remaining seconds from the documented expiry fields."""
        if self.expire_at_ms is not None:
            remaining_ms = self.expire_at_ms - int(time.time() * 1000)
            return max(0, int((remaining_ms + 999) / 1000))
        if self.expire_in_ms is None:
            return None
        return max(0, int(self.expire_in_ms / 1000))

    @property
    def remaining_seconds(self) -> int | None:
        """Compatibility alias for remaining seconds."""
        return self.expires_in_seconds

    @property
    def pollable(self) -> bool:
        """Return whether the qrcode can still be polled."""
        return self.status in {
            ScanLoginStatus.CREATED,
            ScanLoginStatus.SCANNED,
            ScanLoginStatus.CONFIRM,
        }


def account_base_url(region: str) -> str:
    """Return the documented account API base URL for a cloud region."""
    normalized = _normalize_region(region)
    return f"{CLOUD_REGION_BASE_DOMAINS[normalized].rstrip('/')}/apis/account"


def iot_base_url(region: str) -> str:
    """Return the documented IoT API base URL for a cloud region."""
    normalized = _normalize_region(region)
    return f"{CLOUD_REGION_BASE_DOMAINS[normalized].rstrip('/')}/apis/iot"


def build_scan_login_qrcode_path(device: str) -> str:
    """Build the documented qrcode creation endpoint path."""
    return (
        "/user/scan-login/query/qrcode/"
        f"{quote(_required_text(device, 'device'), safe='')}"
    )


def build_scan_login_status_path(qr_code_id: str) -> str:
    """Build the documented qrcode polling endpoint path."""
    return (
        "/user/scan-login/check/qrcode/"
        f"{quote(_required_text(qr_code_id, 'qr_code_id'), safe='')}"
    )


def scan_login_qrcode_path(device: str) -> str:
    """Compatibility alias for qrcode creation path."""
    return build_scan_login_qrcode_path(device)


def scan_login_check_path(qr_code_id: str) -> str:
    """Compatibility alias for qrcode polling path."""
    return build_scan_login_status_path(qr_code_id)


def build_scan_login_qrcode_content(qr_code_id: str, device: str) -> str:
    """Build qrcode content in the documented ``qrcodeid&device`` shape."""
    return (
        f"{_required_text(qr_code_id, 'qr_code_id')}"
        f"&{_required_text(device, 'device')}"
    )


def parse_scan_login_response(payload: Mapping[str, Any]) -> YeelightScanLoginQrCode:
    """Parse a scan-login response body and classify documented errors."""
    raise_for_body_error(payload)
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise ProtocolError("Invalid Yeelight scan-login response")

    status = _required_text(data.get("status"), "status").upper()
    if status not in SCAN_LOGIN_STATUSES:
        raise ProtocolError("Invalid Yeelight scan-login status")

    token_payload = data.get("token")
    token = (
        _parse_scan_login_token(token_payload)
        if status == ScanLoginStatus.LOGIN and token_payload is not None
        else None
    )
    if status == ScanLoginStatus.LOGIN and token is None:
        raise ProtocolError("Invalid Yeelight scan-login token response")

    return YeelightScanLoginQrCode(
        qr_code_id=_required_text(data.get("qrCodeId"), "qrCodeId"),
        device=_required_text(data.get("device"), "device"),
        status=status,
        create_at_ms=_optional_int(data.get("createAt")),
        expire_in_ms=_optional_int(data.get("expireIn")),
        expire_at_ms=_optional_int(data.get("expireAt")),
        source=_optional_text(data.get("source")),
        token=token,
    )


def parse_scan_login_status(payload: Mapping[str, Any]) -> YeelightScanLoginQrCode:
    """Compatibility alias for scan-login response parsing."""
    return parse_scan_login_response(payload)


def _parse_scan_login_token(value: Any) -> YeelightOAuthToken:
    """Parse camelCase scan-login token fields through the shared token model."""
    if not isinstance(value, Mapping):
        raise ProtocolError("Invalid Yeelight scan-login token response")
    return parse_oauth_token_response({
        "access_token": value.get("accessToken"),
        "token_type": value.get("tokenType"),
        "refresh_token": value.get("refreshToken"),
        "expires_in": value.get("expiresIn"),
        "id": value.get("id"),
        "region": value.get("region"),
        "device": value.get("device"),
        "client_id": value.get("clientId"),
        "username": value.get("username"),
        "scope": value.get("scope"),
    })


def _normalize_region(value: str) -> str:
    """Normalize user-facing region aliases to the stored region key."""
    normalized = str(value or "").strip().lower()
    normalized = _REGION_ALIASES.get(normalized, normalized)
    if normalized not in CLOUD_REGION_BASE_DOMAINS:
        raise ProtocolError("Invalid Yeelight cloud region")
    return normalized


def _required_text(value: Any, field: str) -> str:
    """Return a required non-empty text field without echoing the value."""
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f"Yeelight scan-login {field} is required")
    return value.strip()


def _optional_text(value: Any) -> str:
    """Return optional string field with a stable empty fallback."""
    return value.strip() if isinstance(value, str) else ""


def _optional_int(value: Any) -> int | None:
    """Return optional integer field without exposing raw values."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "SCAN_LOGIN_QRCODE_TTL_MS",
    "SCAN_LOGIN_QRCODE_TTL_SECONDS",
    "SCAN_LOGIN_SOURCE_HOME_ASSISTANT",
    "SCAN_LOGIN_STATUS_CONFIRM",
    "SCAN_LOGIN_STATUS_CREATED",
    "SCAN_LOGIN_STATUS_EXPIRED",
    "SCAN_LOGIN_STATUS_LOGIN",
    "SCAN_LOGIN_STATUS_SCANNED",
    "ScanLoginStatus",
    "YeelightScanLoginQrCode",
    "account_base_url",
    "build_scan_login_qrcode_content",
    "build_scan_login_qrcode_path",
    "build_scan_login_status_path",
    "iot_base_url",
    "parse_scan_login_response",
    "parse_scan_login_status",
    "scan_login_check_path",
    "scan_login_qrcode_path",
]
