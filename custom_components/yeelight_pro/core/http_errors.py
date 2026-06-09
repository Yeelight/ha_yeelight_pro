"""Yeelight Open API HTTP/body error classification."""
from __future__ import annotations

from typing import Any, Mapping

from .exceptions import (
    AuthenticationError,
    CommandError,
    RateLimitError,
    ServerError,
    TokenExpiredError,
)


def raise_for_body_error(payload: Mapping[str, Any]) -> None:
    """按开放平台 body code 识别业务错误，避免 HTTP 200 假成功."""
    code = _normalized_body_code(payload.get("code"))
    error = str(payload.get("error") or "").lower()
    if code in {"", "0", "200"} and not error:
        return

    message = str(payload.get("msg") or payload.get("message") or "").lower()
    combined = f"{error} {message} {code}".strip()

    if "invalid_token" in combined or (
        "token" in combined and "invalid" in combined
    ):
        raise TokenExpiredError("Access token expired or invalid")
    if (
        "access_denied" in combined
        or "unauthorized" in combined
        or "forbidden" in combined
        or code in {"401", "403"}
    ):
        raise AuthenticationError("Access denied")
    if "rate" in combined or code == "429":
        raise RateLimitError("Rate limit exceeded")

    numeric_code = _int_or_none(code)
    if numeric_code is not None and numeric_code >= 500:
        raise ServerError(f"Server error: code {numeric_code}")

    raise CommandError(f"Open API request failed: code {code or 'unknown'}")


def _normalized_body_code(value: Any) -> str:
    """归一化开放平台 code 字段."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)) and int(value) == value:
        return str(int(value))
    return str(value).strip()


def _int_or_none(value: Any) -> int | None:
    """把 Open API 可能返回的字符串数字转为 int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
