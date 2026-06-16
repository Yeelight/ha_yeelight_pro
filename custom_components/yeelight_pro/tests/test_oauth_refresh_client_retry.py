"""Client retry-on-401 tests for OAuth refresh handlers."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

from aiohttp import ClientSession
import pytest

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import AuthenticationError


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


class _SequenceSession:
    """Return queued responses for retry-on-401 client tests."""

    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _FakeResponse(200, self.payloads.pop(0))


def _client(session: Any) -> YeelightProClient:
    """Build a Yeelight client backed by a fake session."""
    return YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="access-old",
        client_id="client-old",
        session=cast(ClientSession, session),
    )


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
