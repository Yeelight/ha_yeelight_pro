"""OAuth refresh token regression tests for scan-login cloud entries."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientSession
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.config_flow_scan_login_helpers import (
    scan_login_entry_data,
)
from custom_components.yeelight_pro.const import (
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
    CONF_TOKEN_TYPE,
    CONNECTION_MODE_CLOUD,
    DOMAIN,
)
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import AuthenticationError
from custom_components.yeelight_pro.core.oauth import refresh_access_token
from custom_components.yeelight_pro.entry_migration import normalize_entry_data
from custom_components.yeelight_pro.oauth_refresh import async_refresh_entry_token
from custom_components.yeelight_pro.scan_login_contract import (
    YeelightAccountToken,
    parse_account_token,
)


class _FakeResponse:
    """提供 OAuth refresh 所需的最小 aiohttp response 接口。"""

    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, _exc_type, _exc, _traceback) -> None:
        return None

    async def json(self) -> Any:
        return self._payload


class _FakeOAuthSession:
    """Capture OAuth refresh requests without network I/O."""

    def __init__(self, *, status: int = 200, payload: Any | None = None) -> None:
        self.status = status
        self.payload = payload if payload is not None else _oauth_token_payload()
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return _FakeResponse(self.status, self.payload)


class _SequenceSession:
    """Return queued responses for retry-on-401 client tests."""

    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _FakeResponse(200, self.payloads.pop(0))


def _oauth_token_payload(**overrides: Any) -> dict[str, Any]:
    """Return a documented OAuth token response body."""
    payload = {
        "accessToken": "access-new",
        "tokenType": "bearer",
        "refreshToken": "refresh-new",
        "expiresIn": 7200,
        "scope": "read write",
        "id": 122349,
        "region": "CN",
        "device": "ha-device-new",
        "clientId": "client-new",
        "clientSecret": "secret-new",
        "username": "user-1",
        "jti": "jti-new",
    }
    payload.update(overrides)
    return payload


def _entry_data(**overrides: Any) -> dict[str, Any]:
    """Build refresh-capable normalized cloud entry data."""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_ACCESS_TOKEN: "access-old",
        CONF_REFRESH_TOKEN: "refresh-old",
        CONF_TOKEN_EXPIRES_IN: 1,
        CONF_TOKEN_TYPE: "bearer",
        CONF_CLOUD_REGION: "cn",
        CONF_OPEN_API_CLIENT_ID: "client-old",
        CONF_OPEN_API_CLIENT_SECRET: "secret-old",
        CONF_ACCOUNT_USER_ID: 122349,
        CONF_ACCOUNT_USERNAME: "user-1",
        CONF_SCAN_LOGIN_DEVICE: "ha-device-old",
        "house_id": 1,
    })
    data.update(overrides)
    return data


def _entry(data: dict[str, Any]) -> MagicMock:
    """Build a config-entry test double."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-refresh"
    entry.data = data
    return entry


def _client(session: Any) -> YeelightProClient:
    """Build a Yeelight client backed by a fake session."""
    return YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="access-old",
        client_id="client-old",
        session=cast(ClientSession, session),
    )


def test_parse_account_token_accepts_client_secret_aliases() -> None:
    """OAuth token 解析必须保留 refresh 所需的 clientSecret/client_secret。"""
    token = parse_account_token(_oauth_token_payload(clientSecret="secret-camel"))
    snake = parse_account_token(_oauth_token_payload(
        clientSecret="",
        client_secret="secret-snake",
    ))

    assert token.client_secret == "secret-camel"
    assert snake.client_secret == "secret-snake"
    assert token.refresh_token == "refresh-new"


def test_scan_login_entry_data_persists_client_secret() -> None:
    """扫码登录 entry data 必须保存后续 refresh 所需的 client_secret。"""
    token = YeelightAccountToken(
        access_token="access",
        token_type="bearer",
        refresh_token="refresh",
        expires_in=7200,
        scope="",
        user_id=122349,
        region="CN",
        device="ha-device",
        client_id="client",
        client_secret="secret",
        username="user-1",
        jti="jti",
    )

    data = scan_login_entry_data(token, device="ha-device")

    assert data[CONF_OPEN_API_CLIENT_ID] == "client"
    assert data[CONF_OPEN_API_CLIENT_SECRET] == "secret"


def test_normalize_entry_data_preserves_client_secret_aliases() -> None:
    """旧字段 clientSecret/client_secret 应统一归一到 open_api_client_secret。"""
    camel = normalize_entry_data({"clientSecret": "secret-camel"})
    snake = normalize_entry_data({"client_secret": "secret-snake"})

    assert camel[CONF_OPEN_API_CLIENT_SECRET] == "secret-camel"
    assert snake[CONF_OPEN_API_CLIENT_SECRET] == "secret-snake"


@pytest.mark.asyncio
async def test_refresh_access_token_posts_form_to_region_account_api() -> None:
    """OAuth refresh 应按文档向区域账号 API POST form，不放 JSON body。"""
    session = _FakeOAuthSession()

    token = await refresh_access_token(
        cast(ClientSession, session),
        _client(session).timeout,
        region="us",
        client_id="client-old",
        client_secret="secret-old",
        refresh_token="refresh-old",
    )

    assert token.access_token == "access-new"
    assert session.calls == [{
        "url": "https://api-us.yeelight.com/apis/account/oauth/token",
        "data": {
            "grant_type": "refresh_token",
            "client_id": "client-old",
            "client_secret": "secret-old",
            "refresh_token": "refresh-old",
        },
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        "timeout": _client(session).timeout,
    }]


@pytest.mark.asyncio
async def test_refresh_access_token_400_requires_reauth_without_secret_leak() -> None:
    """refresh token 失效通常返回 400，应归类为鉴权失败且不泄露 secret。"""
    session = _FakeOAuthSession(
        status=400,
        payload={"error": "invalid_grant", "error_description": "secret-old"},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await refresh_access_token(
            cast(ClientSession, session),
            _client(session).timeout,
            region="cn",
            client_id="client-old",
            client_secret="secret-old",
            refresh_token="refresh-old",
        )

    assert "secret-old" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_refresh_entry_token_saves_rotated_refresh_token(
    hass: HomeAssistant,
) -> None:
    """refresh token 一次性轮换成功后必须保存新的 access/refresh/client secret。"""
    hass.data.setdefault(DOMAIN, {})
    hass.config_entries.async_update_entry = MagicMock()
    entry = _entry(_entry_data())
    session = _FakeOAuthSession(payload=_oauth_token_payload())
    client = _client(session)

    result = await async_refresh_entry_token(
        hass,
        entry,
        client,
        force=True,
        session=cast(ClientSession, session),
    )

    assert result.refreshed is True
    assert result.entry_data[CONF_ACCESS_TOKEN] == "access-new"
    assert result.entry_data[CONF_REFRESH_TOKEN] == "refresh-new"
    assert result.entry_data[CONF_OPEN_API_CLIENT_ID] == "client-new"
    assert result.entry_data[CONF_OPEN_API_CLIENT_SECRET] == "secret-new"
    assert result.entry_data[CONF_SCAN_LOGIN_DEVICE] == "ha-device-old"
    assert client.access_token == "access-new"
    assert client.client_id == "client-new"
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        data=result.entry_data,
    )


@pytest.mark.asyncio
async def test_async_refresh_entry_token_preserves_existing_secret_when_response_omits_it(
    hass: HomeAssistant,
) -> None:
    """少数响应不返回新 secret 时，应保留旧 secret 以允许下次 refresh。"""
    hass.data.setdefault(DOMAIN, {})
    entry = _entry(_entry_data())
    session = _FakeOAuthSession(payload=_oauth_token_payload(clientSecret=""))
    client = _client(session)

    result = await async_refresh_entry_token(
        hass,
        entry,
        client,
        force=True,
        update_entry=False,
        session=cast(ClientSession, session),
    )

    assert result.entry_data[CONF_OPEN_API_CLIENT_SECRET] == "secret-old"


@pytest.mark.asyncio
async def test_async_refresh_entry_token_requires_complete_metadata(
    hass: HomeAssistant,
) -> None:
    """缺少 client_secret 时 force refresh 应直接触发 reauth 语义。"""
    hass.data.setdefault(DOMAIN, {})
    entry = _entry(_entry_data(**{CONF_OPEN_API_CLIENT_SECRET: ""}))
    client = _client(_FakeOAuthSession())

    with pytest.raises(AuthenticationError):
        await async_refresh_entry_token(hass, entry, client, force=True)


@pytest.mark.asyncio
async def test_async_refresh_entry_token_rejects_account_mismatch(
    hass: HomeAssistant,
) -> None:
    """refresh 响应账号与 entry 不一致时必须拒绝写入新 token。"""
    hass.data.setdefault(DOMAIN, {})
    hass.config_entries.async_update_entry = MagicMock()
    entry = _entry(_entry_data())
    session = _FakeOAuthSession(payload=_oauth_token_payload(id=998877))
    client = _client(session)

    with pytest.raises(AuthenticationError):
        await async_refresh_entry_token(
            hass,
            entry,
            client,
            force=True,
            session=cast(ClientSession, session),
        )

    hass.config_entries.async_update_entry.assert_not_called()
    assert client.access_token == "access-old"


@pytest.mark.asyncio
async def test_client_retries_once_after_token_refresh() -> None:
    """运行时 401 只 refresh 后重试一次，并使用新 access token。"""
    session = _SequenceSession([
        {"code": "401", "msg": "invalid_token"},
        {"code": "0", "data": {"ok": True}},
    ])
    client = _client(session)
    refresh_handler = AsyncMock()

    async def _refresh() -> None:
        await refresh_handler()
        client.access_token = "access-new"
        client.client_id = "client-new"

    client.set_token_refresh_handler(_refresh)

    result = await client._request("GET", "/v1/open/node/house/1/r/info")

    assert result == {"code": "0", "data": {"ok": True}}
    refresh_handler.assert_awaited_once()
    assert len(session.calls) == 2
    assert session.calls[0]["headers"]["Authorization"] == "Bearer access-old"
    assert session.calls[1]["headers"]["Authorization"] == "Bearer access-new"
    assert session.calls[1]["headers"]["clientId"] == "client-new"


@pytest.mark.asyncio
async def test_client_does_not_retry_token_refresh_twice() -> None:
    """第二次 401 不应无限循环 refresh。"""
    session = _SequenceSession([
        {"code": "401", "msg": "invalid_token"},
        {"code": "401", "msg": "invalid_token"},
    ])
    client = _client(session)
    refresh_handler = AsyncMock()
    client.set_token_refresh_handler(refresh_handler)

    with pytest.raises(AuthenticationError):
        await client._request("GET", "/v1/open/node/house/1/r/info")

    refresh_handler.assert_awaited_once()
    assert len(session.calls) == 2
