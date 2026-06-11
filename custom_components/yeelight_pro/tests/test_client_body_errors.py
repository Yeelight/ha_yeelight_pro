"""Open API body code error handling tests."""
from __future__ import annotations

from typing import Any, cast

from aiohttp import ClientSession
import pytest

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError as YeelightConnectionError,
    RateLimitError,
    ServerError,
    TokenExpiredError,
    safe_error_summary,
)


class _FakeResponse:
    """提供 aiohttp response 需要的最小异步上下文接口."""

    def __init__(self, payload: Any) -> None:
        self.status = 200
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def json(self) -> Any:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


class _FakeSession:
    """提供 client._request 需要的最小 session 接口."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def request(self, *args, **kwargs) -> _FakeResponse:
        return _FakeResponse(self.payload)


def _client(payload: Any) -> YeelightProClient:
    """构造使用固定响应体的 client."""
    return YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=cast(ClientSession, _FakeSession(payload)),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        pytest.param({"code": "401", "msg": "invalid_token"}, TokenExpiredError, id="401"),
        pytest.param({"code": "403", "msg": "forbidden"}, AuthenticationError, id="403"),
        pytest.param({"code": "429", "msg": "rate limit"}, RateLimitError, id="429"),
        pytest.param({"code": "500", "msg": "server"}, ServerError, id="500"),
        pytest.param({"code": "400", "msg": "bad request"}, CommandError, id="400"),
    ],
)
async def test_client_request_maps_open_api_body_code_errors(
    payload: dict,
    expected_error: type[Exception],
) -> None:
    """HTTP 200 里的 Open API code 错误不能被当作成功响应."""
    with pytest.raises(expected_error):
        await _client(payload)._request("GET", "/v1/open/node/house/12345/r/info")


@pytest.mark.asyncio
@pytest.mark.parametrize("success_code", [None, 0, "0", 200, "200"])
async def test_client_request_accepts_success_body_codes(success_code: object) -> None:
    """开放平台成功 code 的不同返回形态都应兼容."""
    payload: dict[str, object] = {"data": {"ok": True}}
    if success_code is not None:
        payload["code"] = success_code

    assert await _client(payload)._request("GET", "/v1/house/r/all") == payload


@pytest.mark.asyncio
async def test_client_request_redacts_open_api_body_error_message() -> None:
    """body msg 可能包含 token/URL/device，异常字符串只能保留 code."""
    with pytest.raises(CommandError) as exc_info:
        await _client({
            "code": "400",
            "msg": (
                "token=secret-token https://api.yeelight.com "
                "house=12345 device=67890"
            ),
        })._request("GET", "/v1/private")

    message = str(exc_info.value)
    assert message == "Open API request failed: code 400"
    assert "secret-token" not in message
    assert "api.yeelight.com" not in message
    assert "12345" not in message
    assert "67890" not in message


@pytest.mark.asyncio
async def test_safe_error_summary_preserves_only_non_sensitive_error_code() -> None:
    """用户可见服务错误应保留安全错误码，但不能泄漏 vendor payload."""
    with pytest.raises(ServerError) as exc_info:
        await _client({
            "code": "500",
            "msg": (
                "token=secret-token https://api.yeelight.com "
                "house=12345 scene=67890"
            ),
        })._request("POST", "/v1/open/control/house/12345/control/w/scenes/67890")

    summary = safe_error_summary(exc_info.value)

    assert summary == "ServerError code 500"
    assert "secret-token" not in summary
    assert "api.yeelight.com" not in summary
    assert "12345" not in summary
    assert "67890" not in summary


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        pytest.param(
            {"error": "invalid_token", "error_description": "secret-token"},
            TokenExpiredError,
            id="invalid-token",
        ),
        pytest.param(
            {"error": "access_denied", "error_description": "house=12345"},
            AuthenticationError,
            id="access-denied",
        ),
        pytest.param(
            {"error": "unsupported_grant_type", "error_description": "device=67890"},
            CommandError,
            id="unknown-openapi-error",
        ),
    ],
)
async def test_client_request_maps_openapi_body_errors_without_code(
    payload: dict[str, str],
    expected_error: type[Exception],
) -> None:
    """无 code 的 OpenAPI error 响应也不能被误判为成功."""
    with pytest.raises(expected_error) as exc_info:
        await _client(payload)._request("GET", "/v1/open/node/house/r/list")

    message = str(exc_info.value)
    assert "secret-token" not in message
    assert "12345" not in message
    assert "67890" not in message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param([{"code": 0}], id="list"),
        pytest.param("token=secret-token house=12345", id="string"),
    ],
)
async def test_client_request_rejects_non_object_json_payloads(payload: Any) -> None:
    """Open API 顶层响应必须是对象，非对象 JSON 不能伪装成成功."""
    with pytest.raises(YeelightConnectionError) as exc_info:
        await _client(payload)._request("GET", "/v1/open/node/house/r/list")

    message = str(exc_info.value)
    assert "Unexpected JSON response type" in message
    assert "secret-token" not in message
    assert "12345" not in message


@pytest.mark.asyncio
async def test_client_request_maps_json_decode_errors_to_connection_error() -> None:
    """JSON 解析失败属于客户端连接边界错误，异常字符串必须脱敏."""
    with pytest.raises(YeelightConnectionError) as exc_info:
        await _client(ValueError("token=secret-token house=12345"))._request(
            "GET",
            "/v1/open/node/house/r/list",
        )

    message = str(exc_info.value)
    assert message == "Invalid JSON response: ValueError"
    assert "secret-token" not in message
    assert "12345" not in message
