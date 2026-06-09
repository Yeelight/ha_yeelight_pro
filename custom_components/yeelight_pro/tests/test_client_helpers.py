"""Yeelight Pro client helper tests."""
from __future__ import annotations

import pytest

from custom_components.yeelight_pro.core.client_paths import (
    automation_action_path,
    house_areas_path,
    house_automations_path,
    house_devices_path,
    house_gateways_path,
    house_groups_path,
    house_list_path,
    house_rooms_path,
    house_scenes_path,
    house_snapshot_path,
    node_properties_control_path,
    node_properties_read_path,
    node_property_read_path,
    nodes_properties_read_path,
    nodes_property_read_path,
    paginated_path,
    product_schema_path,
    scene_execute_path,
)
from custom_components.yeelight_pro.core.client_helpers import (
    control_properties_body,
    list_result,
    read_nodes_properties_body,
    read_nodes_property_body,
    read_properties_body,
)
from custom_components.yeelight_pro.core.exceptions import CommandError


def test_control_properties_body_builds_set_params() -> None:
    """属性 set body 应保留 propName/value 格式和传入顺序."""
    assert control_properties_body(
        command="set",
        params={"p": True, "l": 80},
        duration=250,
    ) == {
        "command": "set",
        "params": [
            {"propName": "p", "value": True},
            {"propName": "l", "value": 80},
        ],
        "duration": 250,
    }


def test_control_properties_body_builds_toggle_params() -> None:
    """属性 toggle body 不应包含 value 字段."""
    assert control_properties_body(
        command="toggle",
        properties=["p"],
        duration=300,
    ) == {
        "command": "toggle",
        "params": [{"propName": "p"}],
        "duration": 300,
    }


def test_read_properties_body_builds_documented_prop_names() -> None:
    """单节点多属性读取 body 使用开放平台文档中的 propNames 字段."""
    assert read_properties_body(["p", "l", "ct"]) == {
        "propNames": ["p", "l", "ct"]
    }
    assert read_properties_body(["l"], index=2) == {
        "propNames": ["l"],
        "index": 2,
    }


def test_multi_node_read_bodies_match_documented_contract() -> None:
    """多节点属性读取 body 必须使用文档字段 resIds/properties."""
    assert read_nodes_property_body([1, "2", 3]) == {"resIds": [1, "2", 3]}
    assert read_nodes_properties_body([1, 2, 3], ["p", "l"]) == {
        "resIds": [1, 2, 3],
        "properties": ["p", "l"],
    }


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"result": [{"id": "result"}], "rows": [{"id": "rows"}]}, [{"id": "result"}]),
        ({"rows": [{"id": "rows"}], "list": [{"id": "list"}]}, [{"id": "rows"}]),
        ({"list": [{"id": "list"}]}, [{"id": "list"}]),
        ({"result": {"id": "not-list"}}, []),
        ({}, []),
    ],
)
def test_list_result_accepts_open_api_list_field_variants(
    data: dict,
    expected: list[dict],
) -> None:
    """列表 helper 优先兼容公开 result，并保留旧 rows/list fallback."""
    assert list_result(data) == expected


def test_client_paths_match_open_api_contract() -> None:
    """Open API 路径构造集中在 client_paths，便于审计和回归."""
    assert house_list_path() == "/v1/open/node/house/r/list"
    assert house_devices_path(12345) == "/v1/open/node/house/12345/devices/r/list"
    assert house_devices_path(12345, room_id=678) == (
        "/v1/open/node/house/12345/devices/r/list?roomId=678"
    )
    assert house_gateways_path(12345) == "/v2/thing/schema/house/12345/gateway/r/info"
    assert house_areas_path(12345) == "/v1/open/node/house/12345/areas/r/list"
    assert house_rooms_path(12345) == "/v1/open/node/house/12345/rooms/r/list"
    assert house_groups_path(12345) == "/v1/open/node/house/12345/groups/r/list"
    assert house_groups_path(12345, room_id="room_1") == (
        "/v1/open/node/house/12345/groups/r/list?roomId=room_1"
    )
    assert house_scenes_path(12345) == "/v1/open/node/house/12345/scenes/r/list"
    assert house_automations_path(12345) == "/v1/automations/12345/r/list"
    assert house_snapshot_path(12345) == "/v1/open/node/house/12345/r/info"
    assert scene_execute_path(12345, "scene_1") == (
        "/v1/open/control/house/12345/control/w/scenes/scene_1"
    )
    assert automation_action_path("auto_1", "trigger") == "/v1/automation/auto_1/trigger"
    assert paginated_path("/v1/example", page=2, page_size=50) == "/v1/example/2/50"
    assert paginated_path(
        "/v1/example?roomId=678",
        page=2,
        page_size=50,
    ) == "/v1/example/2/50?roomId=678"
    assert product_schema_path([100, 101]) == (
        "/v1/thing/schema/product/r/info?pids=100&pids=101"
    )


def test_node_properties_control_path_uses_registry_node_type() -> None:
    """属性控制路径必须使用 registry 中的开放平台 nodeType."""
    assert node_properties_control_path(
        house_id=12345,
        node_kind="device",
        resource_id=67890,
    ) == "/v1/open/control/house/12345/control/2/67890/w/properties"
    assert node_properties_control_path(
        house_id=12345,
        node_kind="group",
        resource_id="group_1",
    ) == "/v1/open/control/house/12345/control/4/group_1/w/properties"
    assert node_properties_read_path(
        house_id=12345,
        node_kind="device",
        resource_id=67890,
    ) == "/v1/open/control/house/12345/control/2/67890/r/properties"
    assert node_property_read_path(
        house_id=12345,
        node_kind="device",
        resource_id=67890,
        property_name="p",
    ) == "/v1/open/control/house/12345/control/2/67890/r/properties/p"
    assert nodes_property_read_path(
        house_id=12345,
        node_kind="device",
        property_name="p",
    ) == "/v1/open/control/house/12345/control/2/r/properties/p"
    assert nodes_properties_read_path(
        house_id=12345,
        node_kind="group",
    ) == "/v1/open/control/house/12345/control/4/r/properties"

    with pytest.raises(CommandError, match="Unsupported control node kind"):
        node_properties_control_path(
            house_id=12345,
            node_kind="scene",
            resource_id="scene_1",
        )
    with pytest.raises(CommandError, match="Unsupported read node kind"):
        node_properties_read_path(
            house_id=12345,
            node_kind="scene",
            resource_id="scene_1",
        )
