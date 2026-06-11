"""Yeelight Pro client pagination tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    ConnectionError as YeelightConnectionError,
)


def _client() -> YeelightProClient:
    """构造分页测试 client."""
    return YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=MagicMock(),
    )


@pytest.mark.asyncio
async def test_client_paginated_rows_reads_all_pages() -> None:
    """分页列表接口必须读取完整 rows，不能只返回第一页."""
    client = _client()
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [
            {"data": {"rows": [{"id": 1}], "total": 3}},
            {"data": {"rows": [{"id": 2}], "total": 3}},
            {"data": {"rows": [{"id": 3}], "total": 3}},
        ]

        rows = await client.get_rooms(12345)

    assert rows == [{"id": 1}, {"id": 2}, {"id": 3}]
    assert [call.args for call in mock_request.await_args_list] == [
        ("GET", "/v1/open/node/house/12345/rooms/r/list/1/200"),
        ("GET", "/v1/open/node/house/12345/rooms/r/list/2/200"),
        ("GET", "/v1/open/node/house/12345/rooms/r/list/3/200"),
    ]


@pytest.mark.asyncio
async def test_client_paginated_rows_accepts_documented_result_field() -> None:
    """公开开放平台列表响应使用 data.result 字段."""
    client = _client()
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [
            {"data": {"result": [{"id": 1}], "total": 2}},
            {"data": {"result": [{"id": 2}], "total": 2}},
        ]

        rows = await client.get_rooms(12345)

    assert rows == [{"id": 1}, {"id": 2}]
    assert [call.args for call in mock_request.await_args_list] == [
        ("GET", "/v1/open/node/house/12345/rooms/r/list/1/200"),
        ("GET", "/v1/open/node/house/12345/rooms/r/list/2/200"),
    ]


@pytest.mark.asyncio
async def test_client_get_houses_uses_documented_paginated_endpoint() -> None:
    """家庭列表应使用开放平台公开分页路径和 result 响应字段."""
    client = _client()
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {
            "data": {"result": [{"houseId": 12345, "houseName": "Home"}], "total": 1}
        }

        houses = await client.get_houses()

    assert houses == [{"houseId": 12345, "houseName": "Home"}]
    mock_request.assert_awaited_once_with(
        "GET",
        "/v1/open/node/house/r/list/1/200",
    )


@pytest.mark.asyncio
async def test_client_get_house_snapshot_uses_documented_endpoint() -> None:
    """家庭/项目概况应使用开放平台 3.1.2 文档路径."""
    client = _client()
    response = {"data": {"houseId": 12345, "houseName": "Home"}}
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = response

        snapshot = await client.get_house_snapshot(12345)

    assert snapshot == response
    mock_request.assert_awaited_once_with(
        "GET",
        "/v1/open/node/house/12345/r/info",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "expected_path"),
    [
        pytest.param(
            "get_devices",
            "/v1/open/node/house/12345/devices/r/list/1/200?roomId=678",
            id="devices",
        ),
        pytest.param(
            "get_groups",
            "/v1/open/node/house/12345/groups/r/list/1/200?roomId=678",
            id="groups",
        ),
    ],
)
async def test_client_room_scoped_lists_keep_query_after_pagination(
    method_name: str,
    expected_path: str,
) -> None:
    """设备/灯组列表支持开放平台 roomId 过滤，分页段必须在 query 前."""
    client = _client()
    method = getattr(client, method_name)
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"data": {"result": [], "total": 0}}

        rows = await method(12345, room_id=678)

    assert rows == []
    mock_request.assert_awaited_once_with("GET", expected_path)


@pytest.mark.asyncio
async def test_client_paginated_rows_accepts_string_total() -> None:
    """真实 Open API 可能把 total 返回为字符串数字."""
    client = _client()
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [
            {"data": {"rows": [{"id": 1}], "total": "2"}},
            {"data": {"rows": [{"id": 2}], "total": "2"}},
        ]

        rows = await client.get_areas(12345)

    assert rows == [{"id": 1}, {"id": 2}]
    assert [call.args for call in mock_request.await_args_list] == [
        ("GET", "/v1/open/node/house/12345/areas/r/list/1/200"),
        ("GET", "/v1/open/node/house/12345/areas/r/list/2/200"),
    ]


@pytest.mark.asyncio
async def test_client_paginated_rows_stops_on_empty_page() -> None:
    """服务端 total 异常偏大时，空页应终止分页读取."""
    client = _client()
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [
            {"data": {"rows": [{"id": 1}], "total": 99}},
            {"data": {"rows": [], "total": 99}},
        ]

        rows = await client.get_areas(12345)

    assert rows == [{"id": 1}]
    assert [call.args for call in mock_request.await_args_list] == [
        ("GET", "/v1/open/node/house/12345/areas/r/list/1/200"),
        ("GET", "/v1/open/node/house/12345/areas/r/list/2/200"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "expected_prefix"),
    [
        ("get_devices", "/v1/open/node/house/12345/devices/r/list"),
        ("get_gateways", "/v2/thing/schema/house/12345/gateway/r/info"),
        ("get_areas", "/v1/open/node/house/12345/areas/r/list"),
        ("get_rooms", "/v1/open/node/house/12345/rooms/r/list"),
        ("get_groups", "/v1/open/node/house/12345/groups/r/list"),
        ("get_scenes", "/v1/open/node/house/12345/scenes/r/list"),
    ],
)
async def test_client_list_methods_use_paginated_endpoints(
    method_name: str,
    expected_prefix: str,
) -> None:
    """所有列表接口都应走统一分页路径."""
    client = _client()
    method = getattr(client, method_name)

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"data": {"rows": [], "total": 0}}

        rows = await method(12345)

    assert rows == []
    mock_request.assert_awaited_once_with("GET", f"{expected_prefix}/1/200")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_error",
    [
        pytest.param(AuthenticationError("forbidden"), id="auth"),
        pytest.param(YeelightConnectionError("offline"), id="network"),
    ],
)
async def test_client_paginated_rows_preserve_request_exceptions(
    request_error: Exception,
) -> None:
    """分页 helper 不吞异常，认证和网络语义继续交给上层处理."""
    client = _client()
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = request_error
        with pytest.raises(type(request_error)) as exc_info:
            await client.get_scenes(12345)

    assert exc_info.value is request_error
