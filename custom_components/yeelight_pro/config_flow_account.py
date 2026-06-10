"""Account identity helpers for Yeelight cloud config flows."""

from __future__ import annotations

import hashlib
from typing import Any

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_OPEN_API_CLIENT_ID,
)

UNKNOWN_ACCOUNT_KEY = "unknown"


def redacted_token_fingerprint(access_token: Any) -> str | None:
    """Return a stable token fingerprint without exposing token material."""
    if not isinstance(access_token, str) or not access_token.strip():
        return None
    digest = hashlib.sha256(access_token.strip().encode("utf-8")).hexdigest()[:16]
    return f"token-{digest}"


def account_identity(
    *,
    account_user_id: Any = None,
    username: Any = "",
    client_id: Any = "",
    access_token: Any = "",
) -> tuple[str, str] | None:
    """Return the strongest non-sensitive account identity for a token."""
    user_id = str(account_user_id).strip() if account_user_id is not None else ""
    if user_id:
        return ("user_id", user_id)
    for key, value in (("username", username), ("client_id", client_id)):
        if isinstance(value, str) and value.strip():
            return (key, value.strip())
    fingerprint = redacted_token_fingerprint(access_token)
    return ("access_token", fingerprint) if fingerprint is not None else None


def account_key_from_identity(identity: tuple[str, str] | None) -> str:
    """Return the unique-id account key for a stored account identity."""
    if identity is None:
        return UNKNOWN_ACCOUNT_KEY
    return identity[1]


def account_key_from_entry_data(entry_data: dict[str, Any]) -> str:
    """Return a stable account key from normalized config-entry data."""
    return account_key_from_identity(account_identity(
        account_user_id=entry_data.get(CONF_ACCOUNT_USER_ID),
        username=entry_data.get(CONF_ACCOUNT_USERNAME, ""),
        client_id=entry_data.get(CONF_OPEN_API_CLIENT_ID, ""),
        access_token=entry_data.get(CONF_ACCESS_TOKEN, ""),
    ))


__all__ = [
    "UNKNOWN_ACCOUNT_KEY",
    "account_identity",
    "account_key_from_entry_data",
    "account_key_from_identity",
    "redacted_token_fingerprint",
]
