"""No-network OAuth contract helpers for the Yeelight Open Platform."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from .core.exceptions import (
    AuthenticationError,
    CommandError,
    ProtocolError,
    TokenExpiredError,
)
from .core.http_errors import raise_for_body_error

DEFAULT_OAUTH_AUTHORIZE_URL = "https://api.yeelight.com/apis/account/oauth/authorize"
DEFAULT_OAUTH_TOKEN_URL = "https://api.yeelight.com/apis/account/oauth/token"
OAUTH_RESPONSE_TYPE_CODE = "code"
OAUTH_GRANT_AUTHORIZATION_CODE = "authorization_code"
OAUTH_GRANT_REFRESH_TOKEN = "refresh_token"


@dataclass(frozen=True, slots=True)
class YeelightOAuthToken:
    """Parsed Yeelight OAuth token response without raw vendor payload."""

    access_token: str
    token_type: str
    refresh_token: str
    expires_in: int
    scope: str
    user_id: int | None
    region: str
    device: str
    client_id: str
    username: str
    jti: str


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str | None = None,
    scope: str | Iterable[str] | None = None,
    skip_confirm: bool = True,
    base_url: str = DEFAULT_OAUTH_AUTHORIZE_URL,
) -> str:
    """Build the Yeelight OAuth authorization URL from documented fields."""
    params: dict[str, str] = {
        "client_id": _required_string(client_id, "client_id"),
        "redirect_uri": _required_string(redirect_uri, "redirect_uri"),
        "response_type": OAUTH_RESPONSE_TYPE_CODE,
        "skip_confirm": "true" if skip_confirm else "false",
    }
    normalized_scope = _normalize_scope(scope)
    if normalized_scope:
        params["scope"] = normalized_scope
    if state is not None:
        params["state"] = _required_string(state, "state")
    return f"{_required_string(base_url, 'base_url')}?{urlencode(params)}"


def build_authorization_code_token_body(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    device: str | None = None,
) -> dict[str, str]:
    """Build the documented authorization-code token request body."""
    body = {
        "client_id": _required_string(client_id, "client_id"),
        "client_secret": _required_string(client_secret, "client_secret"),
        "redirect_uri": _required_string(redirect_uri, "redirect_uri"),
        "grant_type": OAUTH_GRANT_AUTHORIZATION_CODE,
        "code": _required_string(code, "code"),
    }
    if device is not None:
        body["device"] = _required_string(device, "device")
    return body


def build_refresh_token_body(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict[str, str]:
    """Build the documented refresh-token request body."""
    return {
        "client_id": _required_string(client_id, "client_id"),
        "client_secret": _required_string(client_secret, "client_secret"),
        "refresh_token": _required_string(refresh_token, "refresh_token"),
        "grant_type": OAUTH_GRANT_REFRESH_TOKEN,
    }


def parse_oauth_token_response(payload: Mapping[str, Any]) -> YeelightOAuthToken:
    """Parse a Yeelight OAuth token body after applying shared error mapping."""
    raise_for_oauth_error(payload)
    raise_for_body_error(payload)
    access_token = _string_field(payload, "access_token")
    token_type = _string_field(payload, "token_type")
    refresh_token = _string_field(payload, "refresh_token")
    expires_in = _int_field(payload, "expires_in")
    return YeelightOAuthToken(
        access_token=access_token,
        token_type=token_type,
        refresh_token=refresh_token,
        expires_in=expires_in,
        scope=_optional_string(payload, "scope"),
        user_id=_optional_int(payload, "id"),
        region=_optional_string(payload, "region"),
        device=_optional_string(payload, "device"),
        client_id=_optional_string(payload, "client_id"),
        username=_optional_string(payload, "username"),
        jti=_optional_string(payload, "jti"),
    )


def raise_for_oauth_error(payload: Mapping[str, Any]) -> None:
    """Classify documented OAuth error bodies without leaking vendor payloads."""
    combined = _oauth_error_text(payload)
    if not combined:
        return

    if (
        "invalid_token" in combined
        or "invalid refresh token" in combined
        or ("refresh" in combined and "token" in combined and "invalid" in combined)
    ):
        raise TokenExpiredError("Yeelight OAuth token expired or invalid")
    if any(
        token in combined
        for token in (
            "access_denied",
            "insufficient_scope",
            "invalid authorization code",
            "invalid_client",
            "invalid_grant",
            "unauthorized_client",
            "unauthorized_user",
        )
    ):
        raise AuthenticationError("Yeelight OAuth authorization failed")
    if any(
        token in combined
        for token in (
            "invalid_request",
            "invalid_scope",
            "redirect_uri_mismatch",
            "unsupported_grant_type",
            "unsupported_response_type",
        )
    ):
        raise ProtocolError("Unsupported Yeelight OAuth request")
    if _looks_like_oauth_error(payload):
        raise CommandError("Yeelight OAuth request failed")


def _normalize_scope(scope: str | Iterable[str] | None) -> str:
    """Return the documented space-delimited scope value."""
    if scope is None:
        return ""
    if isinstance(scope, str):
        return scope.strip()
    return " ".join(str(item).strip() for item in scope if str(item).strip())


def _required_string(value: Any, field: str) -> str:
    """Return a non-empty string or fail without echoing the value."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Yeelight OAuth {field} is required")
    return value.strip()


def _string_field(payload: Mapping[str, Any], field: str) -> str:
    """Read a required token response string without leaking payload data."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError("Invalid Yeelight OAuth token response")
    return value.strip()


def _int_field(payload: Mapping[str, Any], field: str) -> int:
    """Read a required token response integer without leaking payload data."""
    raw_value = payload.get(field)
    if raw_value is None:
        raise ProtocolError("Invalid Yeelight OAuth token response")
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ProtocolError("Invalid Yeelight OAuth token response") from None
    if value <= 0:
        raise ProtocolError("Invalid Yeelight OAuth token response")
    return value


def _optional_string(payload: Mapping[str, Any], field: str) -> str:
    """Read an optional string field as a stable empty-string fallback."""
    value = payload.get(field)
    return value.strip() if isinstance(value, str) else ""


def _optional_int(payload: Mapping[str, Any], field: str) -> int | None:
    """Read an optional integer field without failing the token contract."""
    raw_value = payload.get(field)
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _oauth_error_text(payload: Mapping[str, Any]) -> str:
    """Return a normalized OAuth error string without exposing it to callers."""
    parts = (
        payload.get("error"),
        payload.get("error_description"),
        payload.get("errorMsg"),
        payload.get("msg"),
        payload.get("message"),
    )
    return " ".join(str(part).lower() for part in parts if part).strip()


def _looks_like_oauth_error(payload: Mapping[str, Any]) -> bool:
    """Return true for documented OAuth error envelopes."""
    if "error" in payload or "error_description" in payload:
        return True
    success = payload.get("success")
    return success is False and (
        "errorMsg" in payload or "msg" in payload or "code" in payload
    )


__all__ = [
    "DEFAULT_OAUTH_AUTHORIZE_URL",
    "DEFAULT_OAUTH_TOKEN_URL",
    "OAUTH_GRANT_AUTHORIZATION_CODE",
    "OAUTH_GRANT_REFRESH_TOKEN",
    "OAUTH_RESPONSE_TYPE_CODE",
    "YeelightOAuthToken",
    "build_authorization_code_token_body",
    "build_authorization_url",
    "build_refresh_token_body",
    "parse_oauth_token_response",
    "raise_for_oauth_error",
]
