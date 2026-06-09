"""Yeelight Open Platform OAuth no-network contract tests."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    CommandError,
    ProtocolError,
    TokenExpiredError,
)
from custom_components.yeelight_pro.oauth_contract import (
    DEFAULT_OAUTH_AUTHORIZE_URL,
    DEFAULT_OAUTH_TOKEN_URL,
    OAUTH_GRANT_AUTHORIZATION_CODE,
    OAUTH_GRANT_REFRESH_TOKEN,
    build_authorization_code_token_body,
    build_authorization_url,
    build_refresh_token_body,
    parse_oauth_token_response,
    raise_for_oauth_error,
)


def test_oauth_authorization_url_matches_open_platform_contract() -> None:
    """OAuth 授权 URL 应只包含文档字段，不携带 token 材料."""
    url = build_authorization_url(
        client_id="client-1",
        redirect_uri="https://ha.example.test/auth/external/callback",
        state="state-1",
        scope=["read", "write"],
        skip_confirm=False,
    )

    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == DEFAULT_OAUTH_AUTHORIZE_URL
    assert parse_qs(parsed.query) == {
        "client_id": ["client-1"],
        "redirect_uri": ["https://ha.example.test/auth/external/callback"],
        "response_type": ["code"],
        "scope": ["read write"],
        "state": ["state-1"],
        "skip_confirm": ["false"],
    }


def test_authorization_code_token_body_matches_open_platform_contract() -> None:
    """授权码换 token 请求体应匹配易来开放平台文档."""
    body = build_authorization_code_token_body(
        client_id="client-1",
        client_secret="secret-1",
        redirect_uri="https://ha.example.test/auth/external/callback",
        code="code-1",
        device="home-assistant",
    )

    assert body == {
        "client_id": "client-1",
        "client_secret": "secret-1",
        "redirect_uri": "https://ha.example.test/auth/external/callback",
        "grant_type": OAUTH_GRANT_AUTHORIZATION_CODE,
        "code": "code-1",
        "device": "home-assistant",
    }


def test_refresh_token_body_matches_open_platform_contract() -> None:
    """refresh token 请求体应匹配易来开放平台文档."""
    body = build_refresh_token_body(
        client_id="client-1",
        client_secret="secret-1",
        refresh_token="refresh-1",
    )

    assert body == {
        "client_id": "client-1",
        "client_secret": "secret-1",
        "refresh_token": "refresh-1",
        "grant_type": OAUTH_GRANT_REFRESH_TOKEN,
    }


def test_oauth_token_url_constant_matches_open_platform_contract() -> None:
    """Token endpoint 常量应与开放平台文档一致."""
    assert DEFAULT_OAUTH_TOKEN_URL == "https://api.yeelight.com/apis/account/oauth/token"


def test_parse_oauth_token_response_returns_stable_model() -> None:
    """token 响应解析后不暴露 raw vendor payload."""
    token = parse_oauth_token_response({
        "access_token": "access-1",
        "token_type": "bearer",
        "refresh_token": "refresh-1",
        "expires_in": "7775999",
        "scope": "read write",
        "id": "122349",
        "region": "CN",
        "device": "home-assistant",
        "client_id": "client-1",
        "username": "user-1",
        "jti": "jti-1",
    })

    assert token.access_token == "access-1"
    assert token.token_type == "bearer"
    assert token.refresh_token == "refresh-1"
    assert token.expires_in == 7775999
    assert token.scope == "read write"
    assert token.user_id == 122349
    assert token.region == "CN"
    assert token.device == "home-assistant"
    assert token.client_id == "client-1"
    assert token.username == "user-1"
    assert token.jti == "jti-1"


@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        pytest.param(
            {"error": "invalid_token", "error_description": "secret-refresh-token"},
            TokenExpiredError,
            id="invalid-token",
        ),
        pytest.param(
            {"error": "access_denied", "error_description": "house=12345"},
            AuthenticationError,
            id="access-denied",
        ),
        pytest.param(
            {"error": "insufficient_scope", "error_description": "scope=secret"},
            AuthenticationError,
            id="insufficient-scope",
        ),
        pytest.param(
            {"error": "unauthorized_client", "error_description": "client=secret"},
            AuthenticationError,
            id="unauthorized-client",
        ),
    ],
)
def test_parse_oauth_token_response_maps_errors_without_leaking_payload(
    payload: dict[str, str],
    expected_error: type[Exception],
) -> None:
    """OAuth 错误必须保留分类，同时不能把敏感响应写进异常字符串."""
    with pytest.raises(expected_error) as exc_info:
        parse_oauth_token_response(payload)

    message = str(exc_info.value)
    assert "secret-refresh-token" not in message
    assert "house=12345" not in message


@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        pytest.param(
            {"error": "invalid_grant", "error_description": "code=secret-code"},
            AuthenticationError,
            id="invalid-grant",
        ),
        pytest.param(
            {"error": "unsupported_grant_type", "error_description": "grant=secret"},
            ProtocolError,
            id="unsupported-grant",
        ),
        pytest.param(
            {"error": "invalid_scope", "error_description": "scope=secret-scope"},
            ProtocolError,
            id="invalid-scope",
        ),
        pytest.param(
            {
                "error": "redirect_uri_mismatch",
                "error_description": "redirect=https://secret.example",
            },
            ProtocolError,
            id="redirect-uri-mismatch",
        ),
        pytest.param(
            {"error": "invalid_request", "error_description": "client=secret-client"},
            ProtocolError,
            id="invalid-request",
        ),
        pytest.param(
            {
                "success": False,
                "code": "400",
                "msg": "token=secret-token",
                "errorMsg": "bad oauth request",
            },
            CommandError,
            id="documented-failure-envelope",
        ),
    ],
)
def test_raise_for_oauth_error_classifies_documented_errors_without_leaking_payload(
    payload: dict[str, object],
    expected_error: type[Exception],
) -> None:
    """文档化 OAuth 错误体应分类明确，异常字符串不能带出 vendor payload."""
    with pytest.raises(expected_error) as exc_info:
        raise_for_oauth_error(payload)

    message = str(exc_info.value)
    assert "secret-code" not in message
    assert "secret-token" not in message
    assert "bad oauth request" not in message


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"access_token": "secret-access"}, id="missing-refresh"),
        pytest.param(
            {
                "access_token": "secret-access",
                "token_type": "bearer",
                "refresh_token": "secret-refresh",
                "expires_in": 0,
            },
            id="invalid-expires",
        ),
    ],
)
def test_parse_oauth_token_response_rejects_invalid_success_payloads(
    payload: dict[str, object],
) -> None:
    """缺字段或非法过期时间不能被视为成功认证."""
    with pytest.raises(ProtocolError) as exc_info:
        parse_oauth_token_response(payload)

    message = str(exc_info.value)
    assert "secret-access" not in message
    assert "secret-refresh" not in message


@pytest.mark.parametrize(
    ("client_id", "redirect_uri"),
    [
        ("", "https://ha.example.test"),
        ("client-1", " "),
    ],
)
def test_oauth_authorization_url_rejects_empty_required_fields(
    client_id: str,
    redirect_uri: str,
) -> None:
    """必填字段为空时失败，错误信息不回显字段值."""
    with pytest.raises(ValueError, match="Yeelight OAuth .* is required"):
        build_authorization_url(client_id=client_id, redirect_uri=redirect_uri)
