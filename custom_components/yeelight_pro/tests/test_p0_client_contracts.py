"""P0 Open API client public-entry and path contract tests."""
from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import CommandError


def test_client_keeps_open_api_methods_after_helper_split() -> None:
    """拆分 helper 后 YeelightProClient 仍必须保留稳定公共入口."""
    expected_methods = {
        "get_houses",
        "get_devices",
        "get_gateways",
        "get_product_schemas",
        "control_device",
        "toggle_device",
        "execute_scene",
        "get_rooms",
        "get_groups",
        "control_group",
        "control_node_properties",
        "control_node_property",
        "control_nodes_property",
        "read_node_property",
        "read_node_properties",
        "read_nodes_property",
        "read_nodes_properties",
        "get_scenes",
        "get_areas",
        "get_house_snapshot",
    }

    for method_name in expected_methods:
        assert callable(getattr(YeelightProClient, method_name))

@pytest.mark.asyncio
async def test_client_control_methods_use_explicit_house_id() -> None:
    """写接口 URL 必须来自显式 house_id，不能依赖隐式 client 状态."""
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=MagicMock(),
    )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.control_device(
            house_id=12345,
            device_id=67890,
            params={"p": True, "l": 80},
            duration=250,
        )
        mock_request.assert_awaited_once_with(
            "POST",
            "/v1/open/control/house/12345/control/2/67890/w/properties",
            json={
                "command": "set",
                "params": [
                    {"propName": "p", "value": True},
                    {"propName": "l", "value": 80},
                ],
                "duration": 250,
            },
        )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.toggle_device(
            house_id=12345,
            device_id=67890,
            properties=["p"],
            duration=300,
        )
        mock_request.assert_awaited_once_with(
            "POST",
            "/v1/open/control/house/12345/control/2/67890/w/properties",
            json={
                "command": "toggle",
                "params": [{"propName": "p"}],
                "duration": 300,
            },
        )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.execute_scene(house_id=12345, scene_id="scene_1")
        mock_request.assert_awaited_once_with(
            "POST",
            "/v1/open/control/house/12345/control/w/scenes/scene_1",
        )
        assert cast(Any, mock_request.await_args).kwargs == {}

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.control_group(
            house_id=12345,
            group_id="group_1",
            params={"p": False},
            duration=400,
        )
        mock_request.assert_awaited_once_with(
            "POST",
            "/v1/open/control/house/12345/control/4/group_1/w/properties",
            json={
                "command": "set",
                "params": [{"propName": "p", "value": False}],
                "duration": 400,
            },
        )


@pytest.mark.asyncio
async def test_client_control_node_properties_rejects_unknown_node_kind() -> None:
    """控制路径必须使用 registry 已知 nodeType，避免拼出未知 Open API 路径."""
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=MagicMock(),
    )

    with (
        patch.object(client, "_request", new_callable=AsyncMock) as mock_request,
        pytest.raises(CommandError, match="Unsupported control node kind"),
    ):
        await client._control_node_properties(
            house_id=12345,
            node_kind="scene",
            resource_id="scene_1",
            command="set",
            params={"p": True},
            duration=250,
        )

    mock_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_client_read_node_properties_uses_documented_read_contract() -> None:
    """只读属性查询必须使用开放平台 r/properties 路径和 propNames body."""
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=MagicMock(),
    )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"data": [{"propId": "p", "value": True}]}

        response = await client.read_node_properties(
            house_id=12345,
            node_kind="device",
            resource_id=67890,
            properties=["p", "l"],
            index=1,
        )

    assert response == {"data": [{"propId": "p", "value": True}]}
    mock_request.assert_awaited_once_with(
        "POST",
        "/v1/open/control/house/12345/control/2/67890/r/properties",
        json={"propNames": ["p", "l"], "index": 1},
    )


@pytest.mark.asyncio
async def test_client_read_property_methods_use_documented_contracts() -> None:
    """只读属性 helper 覆盖单体单属性、多节点单属性和多节点多属性."""
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=MagicMock(),
    )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.read_node_property(
            house_id=12345,
            node_kind="device",
            resource_id=67890,
            property_name="p",
        )
        mock_request.assert_awaited_once_with(
            "POST",
            "/v1/open/control/house/12345/control/2/67890/r/properties/p",
            json={},
        )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.read_nodes_property(
            house_id=12345,
            node_kind="device",
            resource_ids=[1, 2, 3],
            property_name="p",
        )
        mock_request.assert_awaited_once_with(
            "POST",
            "/v1/open/control/house/12345/control/2/r/properties/p",
            json={"resIds": [1, 2, 3]},
        )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.read_nodes_properties(
            house_id=12345,
            node_kind="group",
            resource_ids=["g1", "g2"],
            properties=["p", "l"],
        )
        mock_request.assert_awaited_once_with(
            "POST",
            "/v1/open/control/house/12345/control/4/r/properties",
            json={"resIds": ["g1", "g2"], "properties": ["p", "l"]},
        )
