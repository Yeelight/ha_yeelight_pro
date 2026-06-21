"""Yeelight Pro product schema client helper tests."""
from __future__ import annotations

import pytest

from custom_components.yeelight_pro.core.client_helpers import get_product_schemas
from custom_components.yeelight_pro.core.exceptions import CommandError, TokenExpiredError


@pytest.mark.asyncio
async def test_get_product_schemas_merges_public_v1_and_authenticated_v2() -> None:
    """产品 schema 应合并 v1/v2，以补齐组件、事件和动作."""
    calls: list[dict[str, object]] = []

    async def request(method: str, path: str, **kwargs: object) -> dict:
        calls.append({"method": method, "path": path, **kwargs})
        if "/v2/" in path:
            return {
                "data": [{
                    "pid": 100,
                    "components": [
                        {
                            "cid": 1,
                            "index": 1,
                            "properties": [{"propId": "ct", "desc": "Color temp"}],
                            "events": [{"eventId": 7, "name": "pressed"}],
                        }
                    ],
                    "customComponents": [{"cid": 2, "index": 1, "name": "custom"}],
                    "supportActions": [{"actionName": "identify"}],
                }]
            }
        return {
            "data": {
                "schemas": [{
                    "pid": 100,
                    "name": "Lamp",
                    "components": [{
                        "cid": 1,
                        "index": 1,
                        "properties": [{"propId": "p", "desc": "Power"}],
                    }],
                }]
            }
        }

    schemas = await get_product_schemas(request, [100])

    assert schemas == {
        100: {
            "pid": 100,
            "name": "Lamp",
            "components": [
                {
                    "cid": 1,
                    "index": 1,
                    "properties": [
                        {"propId": "p", "desc": "Power"},
                        {"propId": "ct", "desc": "Color temp"},
                    ],
                    "events": [{"eventId": 7, "name": "pressed"}],
                }
            ],
            "customComponents": [{"cid": 2, "index": 1, "name": "custom"}],
            "supportActions": [{"actionName": "identify"}],
        }
    }
    assert calls == [
        {
            "method": "GET",
            "path": "/v1/thing/schema/product/r/info?pids=100",
            "with_auth": False,
        },
        {
            "method": "GET",
            "path": "/v2/thing/schema/product/r/info?pids=100",
            "with_auth": False,
        },
    ]


@pytest.mark.asyncio
async def test_get_product_schemas_retries_with_auth_for_private_endpoint() -> None:
    """私有部署 schema 端点若要求认证，应带当前 token 重试并继续合并 v2."""
    calls: list[dict[str, object]] = []

    async def request(method: str, path: str, **kwargs: object) -> dict:
        calls.append({"method": method, "path": path, **kwargs})
        if len(calls) == 1:
            raise TokenExpiredError("private schema endpoint requires auth")
        if "/v2/" in path and not kwargs.get("with_auth"):
            raise TokenExpiredError("private schema v2 endpoint requires auth")
        if "/v2/" in path:
            return {"data": [{"productId": "101", "desc": "Private schema"}]}
        return {"data": {"schemas": [{"productId": "101", "name": "Panel"}]}}

    schemas = await get_product_schemas(request, [101])

    assert schemas == {
        101: {
            "productId": "101",
            "name": "Panel",
            "desc": "Private schema",
        }
    }
    assert calls == [
        {
            "method": "GET",
            "path": "/v1/thing/schema/product/r/info?pids=101",
            "with_auth": False,
        },
        {
            "method": "GET",
            "path": "/v1/thing/schema/product/r/info?pids=101",
            "with_auth": True,
        },
        {
            "method": "GET",
            "path": "/v2/thing/schema/product/r/info?pids=101",
            "with_auth": False,
        },
        {
            "method": "GET",
            "path": "/v2/thing/schema/product/r/info?pids=101",
            "with_auth": True,
        },
    ]


@pytest.mark.asyncio
async def test_get_product_schemas_falls_back_to_private_v2_endpoint() -> None:
    """私有部署 v1 schema 404 时，应使用认证 v2 端点和列表形态响应."""
    calls: list[dict[str, object]] = []

    async def request(method: str, path: str, **kwargs: object) -> dict:
        calls.append({"method": method, "path": path, **kwargs})
        if len(calls) == 1:
            raise TokenExpiredError("private schema endpoint requires auth")
        if len(calls) == 2:
            raise CommandError("HTTP 404 request failed")
        return {"data": [{"pid": 14338, "name": "Private Gateway"}]}

    schemas = await get_product_schemas(request, [14338])

    assert schemas == {14338: {"pid": 14338, "name": "Private Gateway"}}
    assert calls == [
        {
            "method": "GET",
            "path": "/v1/thing/schema/product/r/info?pids=14338",
            "with_auth": False,
        },
        {
            "method": "GET",
            "path": "/v1/thing/schema/product/r/info?pids=14338",
            "with_auth": True,
        },
        {
            "method": "GET",
            "path": "/v2/thing/schema/product/r/info?pids=14338",
            "with_auth": False,
        },
    ]


@pytest.mark.asyncio
async def test_get_product_schemas_keeps_v1_when_v2_endpoint_fails() -> None:
    """v2 端点异常时，已读取到的 v1 schema 不能被丢弃."""
    calls: list[dict[str, object]] = []

    async def request(method: str, path: str, **kwargs: object) -> dict:
        calls.append({"method": method, "path": path, **kwargs})
        if "/v2/" in path:
            raise CommandError("HTTP 500 request failed")
        return {"data": {"schemas": [{"pid": 102, "name": "Relay"}]}}

    schemas = await get_product_schemas(request, [102])

    assert schemas == {102: {"pid": 102, "name": "Relay"}}
    assert calls == [
        {
            "method": "GET",
            "path": "/v1/thing/schema/product/r/info?pids=102",
            "with_auth": False,
        },
        {
            "method": "GET",
            "path": "/v2/thing/schema/product/r/info?pids=102",
            "with_auth": False,
        },
    ]
