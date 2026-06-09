"""Open API 属性控制合同测试."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.client_helpers import (
    control_nodes_property_body,
    control_properties_body,
    control_property_body,
)
from custom_components.yeelight_pro.core.client_paths import (
    node_properties_control_path,
    node_property_control_path,
    nodes_property_control_path,
)


def test_single_property_control_body_matches_documented_contract() -> None:
    """单属性控制 body 使用 command/value 以及可选执行字段."""
    assert control_property_body(command="set", value=10) == {
        "command": "set",
        "value": 10,
    }
    assert control_property_body(
        command="toggle",
        duration=250,
        delay=100,
        index=1,
        category="light",
    ) == {
        "command": "toggle",
        "duration": 250,
        "delay": 100,
        "index": 1,
        "category": "light",
    }


def test_multi_node_property_control_body_matches_documented_contract() -> None:
    """多节点单属性控制 body 使用 resIds/command/value。"""
    assert control_nodes_property_body(
        resource_ids=[1, "2", 3],
        command="set",
        value=80,
        duration=300,
        delay=50,
        category="light",
    ) == {
        "resIds": [1, "2", 3],
        "command": "set",
        "value": 80,
        "duration": 300,
        "delay": 50,
        "category": "light",
    }


def test_single_node_multi_property_control_body_matches_documented_contract() -> None:
    """单节点多属性控制 body 使用 params 列表和可选执行字段."""
    assert control_properties_body(
        command="set",
        params={"l": 10, "ct": 3000},
        duration=300,
        delay=50,
        index=1,
        category="light",
    ) == {
        "command": "set",
        "params": [
            {"propName": "l", "value": 10},
            {"propName": "ct", "value": 3000},
        ],
        "duration": 300,
        "delay": 50,
        "index": 1,
        "category": "light",
    }
    assert control_properties_body(
        command="toggle",
        properties=["p"],
    ) == {
        "command": "toggle",
        "params": [{"propName": "p"}],
    }


def test_property_control_paths_match_documented_contract() -> None:
    """属性控制路径覆盖单节点和多节点形态."""
    assert node_properties_control_path(
        house_id=12345,
        node_kind="device",
        resource_id=67890,
    ) == "/v1/open/control/house/12345/control/2/67890/w/properties"
    assert node_property_control_path(
        house_id=12345,
        node_kind="device",
        resource_id=67890,
        property_name="l",
    ) == "/v1/open/control/house/12345/control/2/67890/w/properties/l"
    assert nodes_property_control_path(
        house_id=12345,
        node_kind="group",
        property_name="p",
    ) == "/v1/open/control/house/12345/control/4/w/properties/p"


@pytest.mark.asyncio
async def test_client_control_property_methods_use_documented_contracts() -> None:
    """client 层只暴露底层 Open API 控制合同，不发布新 HA 服务."""
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=MagicMock(),
    )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"code": "200"}
        response = await client.control_node_properties(
            house_id=12345,
            node_kind="device",
            resource_id=67890,
            command="set",
            params={"l": 10, "ct": 3000},
            duration=250,
            delay=100,
            index=1,
            category="light",
        )

    assert response == {"code": "200"}
    mock_request.assert_awaited_once_with(
        "POST",
        "/v1/open/control/house/12345/control/2/67890/w/properties",
        json={
            "command": "set",
            "params": [
                {"propName": "l", "value": 10},
                {"propName": "ct", "value": 3000},
            ],
            "duration": 250,
            "delay": 100,
            "index": 1,
            "category": "light",
        },
    )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"code": "200"}
        response = await client.control_node_property(
            house_id=12345,
            node_kind="device",
            resource_id=67890,
            property_name="l",
            command="set",
            value=10,
            duration=250,
            delay=100,
            index=1,
            category="light",
        )

    assert response == {"code": "200"}
    mock_request.assert_awaited_once_with(
        "POST",
        "/v1/open/control/house/12345/control/2/67890/w/properties/l",
        json={
            "command": "set",
            "value": 10,
            "duration": 250,
            "delay": 100,
            "index": 1,
            "category": "light",
        },
    )

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.control_nodes_property(
            house_id=12345,
            node_kind="device",
            resource_ids=[1, 2, 3],
            property_name="l",
            command="set",
            value=10,
            duration=250,
            delay=100,
            category="light",
        )

    mock_request.assert_awaited_once_with(
        "POST",
        "/v1/open/control/house/12345/control/2/w/properties/l",
        json={
            "resIds": [1, 2, 3],
            "command": "set",
            "value": 10,
            "duration": 250,
            "delay": 100,
            "category": "light",
        },
    )
