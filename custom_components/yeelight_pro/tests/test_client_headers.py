"""Yeelight Pro client header contract tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.yeelight_pro.core.client import YeelightProClient


def _client(
    access_token: str = "test-token",
    client_id: str | None = None,
) -> YeelightProClient:
    """构造请求头测试 client."""
    return YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token=access_token,
        client_id=client_id,
        session=MagicMock(),
    )


def test_client_headers_include_bearer_token_by_default() -> None:
    """默认请求必须发送 Bearer token."""
    headers = _client()._get_headers()

    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"
    assert headers["Authorization"] == "Bearer test-token"
    assert "clientId" not in headers


def test_client_headers_include_open_api_client_id_when_available() -> None:
    """账号元数据包含 client_id 后，Open API 请求应带 clientId 头."""
    headers = _client(client_id=" client-1 ")._get_headers()

    assert headers["Authorization"] == "Bearer test-token"
    assert headers["clientId"] == "client-1"


def test_client_headers_omit_authorization_when_auth_disabled() -> None:
    """公开 schema 等接口使用 with_auth=False 时不能携带 token."""
    headers = _client()._get_headers(with_auth=False)

    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"
    assert "Authorization" not in headers
    assert "clientId" not in headers


def test_client_headers_omit_empty_token() -> None:
    """空 token 不应生成无效 Authorization 头."""
    headers = _client(access_token="")._get_headers()

    assert "Authorization" not in headers
