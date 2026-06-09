"""P0 OAuth token runtime contract tests."""

from __future__ import annotations

from typing import cast

from aiohttp import ClientSession
import pytest

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    TokenExpiredError,
)
from custom_components.yeelight_pro.oauth_contract import (
    DEFAULT_OAUTH_TOKEN_URL,
    OAUTH_GRANT_AUTHORIZATION_CODE,
    OAUTH_GRANT_REFRESH_TOKEN,
)

from .p0_client_helpers import FakeOAuthSession


@pytest.mark.asyncio
async def test_client_exchanges_authorization_code_with_documented_oauth_body() -> None:
    """OAuth 授权码换 token 应使用账号 token endpoint 和文档表单字段."""
    session = FakeOAuthSession()
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="manual-token",
        session=cast(ClientSession, session),
    )

    token = await client.exchange_authorization_code(
        client_id="client-1",
        client_secret="secret-1",
        redirect_uri="https://ha.example.test/auth/external/callback",
        code="code-1",
        device="home-assistant",
    )

    assert token.access_token == "access-1"
    assert token.refresh_token == "refresh-2"
    assert session.calls == [
        {
            "url": DEFAULT_OAUTH_TOKEN_URL,
            "data": {
                "client_id": "client-1",
                "client_secret": "secret-1",
                "redirect_uri": "https://ha.example.test/auth/external/callback",
                "grant_type": OAUTH_GRANT_AUTHORIZATION_CODE,
                "code": "code-1",
                "device": "home-assistant",
            },
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            "timeout": client.timeout,
        }
    ]


@pytest.mark.asyncio
async def test_client_refreshes_oauth_token_with_documented_body() -> None:
    """refresh token 运行时能力必须匹配开放平台单次 refresh token 契约."""
    session = FakeOAuthSession()
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="manual-token",
        session=cast(ClientSession, session),
    )

    token = await client.refresh_oauth_token(
        client_id="client-1",
        client_secret="secret-1",
        refresh_token="refresh-1",
    )

    assert token.access_token == "access-1"
    assert session.calls[0]["url"] == DEFAULT_OAUTH_TOKEN_URL
    assert session.calls[0]["data"] == {
        "client_id": "client-1",
        "client_secret": "secret-1",
        "refresh_token": "refresh-1",
        "grant_type": OAUTH_GRANT_REFRESH_TOKEN,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "payload", "expected_error"),
    [
        pytest.param(
            400,
            {"error": "Invalid refresh token", "error_description": "secret-refresh"},
            TokenExpiredError,
            id="invalid-refresh-token",
        ),
        pytest.param(
            401,
            {"error": "invalid_client", "error_description": "secret-client"},
            AuthenticationError,
            id="invalid-client-http-401",
        ),
        pytest.param(
            400,
            {"error": "invalid_grant", "error_description": "secret-code"},
            AuthenticationError,
            id="invalid-authorization-code",
        ),
    ],
)
async def test_client_oauth_token_errors_are_classified_without_payload_leaks(
    status: int,
    payload: dict[str, object],
    expected_error: type[AuthenticationError],
) -> None:
    """OAuth token 失败不能降级为普通连接失败，也不能泄露响应正文."""
    session = FakeOAuthSession(status=status, payload=payload)
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="manual-token",
        session=cast(ClientSession, session),
    )

    with pytest.raises(expected_error) as exc_info:
        await client.refresh_oauth_token(
            client_id="client-1",
            client_secret="secret-1",
            refresh_token="refresh-1",
        )

    message = str(exc_info.value)
    assert "secret-refresh" not in message
    assert "secret-client" not in message
    assert "secret-code" not in message
