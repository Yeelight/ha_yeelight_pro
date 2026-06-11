"""Yeelight Open API path builders used by the HTTP client."""

from __future__ import annotations

from urllib.parse import urlencode

from ..capabilities.registry import node_type
from .exceptions import CommandError


def house_list_path() -> str:
    """用户家庭列表路径。"""
    return "/v1/open/node/house/r/list"


def house_devices_path(house_id: int, *, room_id: int | str | None = None) -> str:
    """家庭设备列表路径。"""
    return _with_query(
        f"/v1/open/node/house/{house_id}/devices/r/list",
        {"roomId": room_id},
    )


def house_gateways_path(house_id: int) -> str:
    """家庭网关列表路径。"""
    return f"/v2/thing/schema/house/{house_id}/gateway/r/info"


def house_rooms_path(house_id: int) -> str:
    """家庭房间列表路径。"""
    return f"/v1/open/node/house/{house_id}/rooms/r/list"


def house_groups_path(house_id: int, *, room_id: int | str | None = None) -> str:
    """家庭灯组列表路径。"""
    return _with_query(
        f"/v1/open/node/house/{house_id}/groups/r/list",
        {"roomId": room_id},
    )


def house_scenes_path(house_id: int) -> str:
    """家庭场景列表路径。"""
    return f"/v1/open/node/house/{house_id}/scenes/r/list"


def house_areas_path(house_id: int) -> str:
    """家庭区域列表路径。"""
    return f"/v1/open/node/house/{house_id}/areas/r/list"


def house_snapshot_path(house_id: int) -> str:
    """家庭快照路径。"""
    return f"/v1/open/node/house/{house_id}/r/info"


def scene_execute_path(house_id: int, scene_id: str) -> str:
    """场景执行路径。"""
    return f"/v1/open/control/house/{house_id}/control/w/scenes/{scene_id}"


def node_properties_control_path(
    *,
    house_id: int,
    node_kind: str,
    resource_id: int | str,
) -> str:
    """按开放平台 nodeType 构造节点属性控制路径。"""
    node_type_id = node_type(node_kind)
    if node_type_id is None:
        raise CommandError(f"Unsupported control node kind: {node_kind}")
    return (
        f"/v1/open/control/house/{house_id}/control/"
        f"{node_type_id}/{resource_id}/w/properties"
    )


def node_property_control_path(
    *,
    house_id: int,
    node_kind: str,
    resource_id: int | str,
    property_name: str,
) -> str:
    """按开放平台 nodeType 构造单节点单属性控制路径。"""
    base_path = node_properties_control_path(
        house_id=house_id,
        node_kind=node_kind,
        resource_id=resource_id,
    )
    return f"{base_path}/{property_name}"


def nodes_property_control_path(
    *,
    house_id: int,
    node_kind: str,
    property_name: str,
) -> str:
    """按开放平台 nodeType 构造多节点单属性控制路径。"""
    node_type_id = node_type(node_kind)
    if node_type_id is None:
        raise CommandError(f"Unsupported control node kind: {node_kind}")
    return (
        f"/v1/open/control/house/{house_id}/control/"
        f"{node_type_id}/w/properties/{property_name}"
    )


def node_properties_read_path(
    *,
    house_id: int,
    node_kind: str,
    resource_id: int | str,
) -> str:
    """按开放平台 nodeType 构造节点属性读取路径。"""
    node_type_id = node_type(node_kind)
    if node_type_id is None:
        raise CommandError(f"Unsupported read node kind: {node_kind}")
    return (
        f"/v1/open/control/house/{house_id}/control/"
        f"{node_type_id}/{resource_id}/r/properties"
    )


def node_property_read_path(
    *,
    house_id: int,
    node_kind: str,
    resource_id: int | str,
    property_name: str,
) -> str:
    """按开放平台 nodeType 构造单节点单属性读取路径。"""
    base_path = node_properties_read_path(
        house_id=house_id,
        node_kind=node_kind,
        resource_id=resource_id,
    )
    return f"{base_path}/{property_name}"


def nodes_property_read_path(
    *,
    house_id: int,
    node_kind: str,
    property_name: str,
) -> str:
    """按开放平台 nodeType 构造多节点单属性读取路径。"""
    node_type_id = node_type(node_kind)
    if node_type_id is None:
        raise CommandError(f"Unsupported read node kind: {node_kind}")
    return (
        f"/v1/open/control/house/{house_id}/control/"
        f"{node_type_id}/r/properties/{property_name}"
    )


def nodes_properties_read_path(
    *,
    house_id: int,
    node_kind: str,
) -> str:
    """按开放平台 nodeType 构造多节点多属性读取路径。"""
    node_type_id = node_type(node_kind)
    if node_type_id is None:
        raise CommandError(f"Unsupported read node kind: {node_kind}")
    return f"/v1/open/control/house/{house_id}/control/{node_type_id}/r/properties"


def product_schema_path(product_ids: list[int]) -> str:
    """产品规格批量读取路径。"""
    pids_param = "&".join(f"pids={pid}" for pid in product_ids)
    return f"/v1/thing/schema/product/r/info?{pids_param}"


def paginated_path(path_prefix: str, *, page: int, page_size: int) -> str:
    """分页列表路径。"""
    path, separator, query = path_prefix.partition("?")
    paged_path = f"{path}/{page}/{page_size}"
    return f"{paged_path}{separator}{query}" if separator else paged_path


def _with_query(path: str, params: dict[str, int | str | None]) -> str:
    """追加 Open API 查询参数，忽略未设置的过滤项。"""
    query = urlencode({
        key: value
        for key, value in params.items()
        if value is not None and str(value) != ""
    })
    return f"{path}?{query}" if query else path
