"""Private-deployment OAuth refresh regression tests."""

from __future__ import annotations

from typing import cast

from aiohttp import ClientSession
import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_OPEN_API_CLIENT_SECRET,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_PRIVATE,
    DOMAIN,
)
from custom_components.yeelight_pro.core.exceptions import AuthenticationError
from custom_components.yeelight_pro.core.oauth import refresh_access_token
from custom_components.yeelight_pro.oauth_refresh import async_refresh_entry_token

from .test_oauth_refresh import (
    _client,
    _entry,
    _entry_data,
    _FakeOAuthSession,
    _oauth_token_payload,
)


@pytest.mark.asyncio
async def test_refresh_access_token_requires_client_secret() -> None:
    """OAuth refresh 仍需 documented client_secret，WebSocket 早断开不能触发弱化认证."""
    session = _FakeOAuthSession()

    with pytest.raises(AuthenticationError):
        await refresh_access_token(
            cast(ClientSession, session),
            _client(session).timeout,
            region="cn",
            client_id="client-old",
            client_secret="",
            refresh_token="refresh-old",
            base_url="http://private.example/apis/account",
        )

    assert session.calls == []


@pytest.mark.asyncio
async def test_refresh_access_token_accepts_private_account_base_url() -> None:
    """私有部署 OAuth refresh 应允许显式 Account API base URL。"""
    session = _FakeOAuthSession()

    await refresh_access_token(
        cast(ClientSession, session),
        _client(session).timeout,
        region="cn",
        client_id="client-old",
        client_secret="secret-old",
        refresh_token="refresh-old",
        base_url="http://private.example/apis/account",
    )

    assert session.calls[0]["url"] == "http://private.example/apis/account/oauth/token"


@pytest.mark.asyncio
async def test_async_refresh_entry_token_private_mode_requires_client_secret(
    hass: HomeAssistant,
) -> None:
    """私有部署 entry 缺 client_secret 也不能把 WebSocket 问题降级成弱 refresh。"""
    hass.data.setdefault(DOMAIN, {})
    entry = _entry(_entry_data(
        **{
            CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
            CONF_PRIVATE_DOMAIN: "http://private.example/apis/iot",
            CONF_OPEN_API_CLIENT_SECRET: "",
        }
    ))
    session = _FakeOAuthSession(payload={"code": "200", "data": _oauth_token_payload()})
    client = _client(session)

    with pytest.raises(AuthenticationError):
        await async_refresh_entry_token(
            hass,
            entry,
            client,
            force=True,
            update_entry=False,
            session=cast(ClientSession, session),
        )

    assert session.calls == []


@pytest.mark.asyncio
async def test_async_refresh_entry_token_private_mode_uses_private_account_api(
    hass: HomeAssistant,
) -> None:
    """私有部署扫码 token 刷新必须发往私有 Account API，而不是公有云区域。"""
    hass.data.setdefault(DOMAIN, {})
    entry = _entry(_entry_data(
        **{
            CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
            CONF_PRIVATE_DOMAIN: "http://private.example/apis/iot",
        }
    ))
    session = _FakeOAuthSession(payload=_oauth_token_payload())
    client = _client(session)

    result = await async_refresh_entry_token(
        hass,
        entry,
        client,
        force=True,
        update_entry=False,
        session=cast(ClientSession, session),
    )

    assert result.refreshed is True
    assert result.entry_data[CONF_PRIVATE_DOMAIN] == "http://private.example"
    assert session.calls[0]["url"] == "http://private.example/apis/account/oauth/token"
