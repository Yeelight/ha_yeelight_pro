"""Config-entry OAuth refresh orchestration for Yeelight Pro."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping

from aiohttp import ClientSession, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .config_flow_account import account_identity
from .config_flow_scan_login_helpers import scan_login_entry_data
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_OPEN_API_CLIENT_ID,
    CONF_OPEN_API_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONNECTION_MODE_CLOUD,
    DEFAULT_CLOUD_REGION,
    DEFAULT_REQUEST_TIMEOUT,
    DOMAIN,
)
from .core.client import YeelightProClient
from .core.exceptions import AuthenticationError
from .core.oauth import refresh_access_token
from .entry_migration import normalize_entry_data
from .scan_login_contract import YeelightAccountToken

_REFRESH_LOCKS_KEY = "oauth_refresh_locks"


@dataclass(frozen=True, slots=True)
class OAuthRefreshResult:
    """Result of a token refresh attempt."""

    refreshed: bool
    entry_data: dict[str, Any]


async def async_refresh_entry_token(
    hass: HomeAssistant,
    entry: ConfigEntry,
    client: YeelightProClient,
    *,
    force: bool = False,
    update_entry: bool = True,
    session: ClientSession | None = None,
) -> OAuthRefreshResult:
    """Refresh a cloud scan-login token when metadata is complete."""
    data = normalize_entry_data(entry.data)
    if not _can_refresh(data):
        if force:
            raise AuthenticationError("Yeelight OAuth refresh metadata is incomplete")
        return OAuthRefreshResult(False, data)

    if not force and not _token_needs_refresh(data):
        return OAuthRefreshResult(False, data)

    lock = _entry_refresh_lock(hass, entry.entry_id)
    async with lock:
        data = normalize_entry_data(entry.data)
        if not _can_refresh(data):
            raise AuthenticationError("Yeelight OAuth refresh metadata is incomplete")
        if not force and not _token_needs_refresh(data):
            client.access_token = data[CONF_ACCESS_TOKEN]
            client.client_id = data.get(CONF_OPEN_API_CLIENT_ID, "")
            return OAuthRefreshResult(False, data)

        token = await refresh_access_token(
            session or client.session,
            getattr(client, "timeout", ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)),
            region=data.get(CONF_CLOUD_REGION) or DEFAULT_CLOUD_REGION,
            client_id=data[CONF_OPEN_API_CLIENT_ID],
            client_secret=data[CONF_OPEN_API_CLIENT_SECRET],
            refresh_token=data[CONF_REFRESH_TOKEN],
        )
        _guard_same_account(data, token)
        new_data = normalize_entry_data({
            **data,
            **scan_login_entry_data(
                token,
                device=data.get(CONF_SCAN_LOGIN_DEVICE) or token.device,
            ),
        })
        if update_entry:
            hass.config_entries.async_update_entry(entry, data=new_data)
        client.access_token = new_data[CONF_ACCESS_TOKEN]
        client.client_id = new_data.get(CONF_OPEN_API_CLIENT_ID, "")
        return OAuthRefreshResult(True, new_data)


async def async_request_with_token_refresh(
    hass: HomeAssistant,
    entry: ConfigEntry,
    client: YeelightProClient,
    request: Any,
) -> Any:
    """Run one client request, refresh on 401, then retry once."""
    try:
        return await request()
    except AuthenticationError:
        await async_refresh_entry_token(hass, entry, client, force=True)
        return await request()


def _can_refresh(data: Mapping[str, Any]) -> bool:
    """Return whether the entry carries the documented refresh parameters."""
    return (
        data.get(CONF_CONNECTION_MODE) == CONNECTION_MODE_CLOUD
        and bool(_string(data.get(CONF_REFRESH_TOKEN)))
        and bool(_string(data.get(CONF_OPEN_API_CLIENT_ID)))
        and bool(_string(data.get(CONF_OPEN_API_CLIENT_SECRET)))
    )


def _token_needs_refresh(data: Mapping[str, Any]) -> bool:
    """Return whether a stored access token should be refreshed proactively."""
    expires_in = data.get(CONF_TOKEN_EXPIRES_IN)
    if not isinstance(expires_in, int):
        return False
    return expires_in <= 3600


def _guard_same_account(
    entry_data: Mapping[str, Any],
    token: YeelightAccountToken,
) -> None:
    """Reject refresh responses that point at a different known account."""
    expected = account_identity(
        account_user_id=entry_data.get(CONF_ACCOUNT_USER_ID),
        username=entry_data.get(CONF_ACCOUNT_USERNAME, ""),
        client_id=entry_data.get(CONF_OPEN_API_CLIENT_ID, ""),
        access_token=entry_data.get(CONF_ACCESS_TOKEN, ""),
    )
    actual = account_identity(
        account_user_id=token.user_id,
        username=token.username,
        client_id=token.client_id,
        access_token=token.access_token,
    )
    if expected is not None and actual is not None and expected != actual:
        raise AuthenticationError("Yeelight OAuth refresh account mismatch")


def _entry_refresh_lock(hass: HomeAssistant, entry_id: str) -> asyncio.Lock:
    """Return one OAuth refresh lock per config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    locks = domain_data.setdefault(_REFRESH_LOCKS_KEY, {})
    if not isinstance(locks, dict):
        locks = {}
        domain_data[_REFRESH_LOCKS_KEY] = locks
    lock = locks.get(entry_id)
    if not isinstance(lock, asyncio.Lock):
        lock = asyncio.Lock()
        locks[entry_id] = lock
    return lock


def _string(value: Any) -> str:
    """Return value as stripped text."""
    return value.strip() if isinstance(value, str) else ""


__all__ = [
    "OAuthRefreshResult",
    "async_refresh_entry_token",
    "async_request_with_token_refresh",
]
