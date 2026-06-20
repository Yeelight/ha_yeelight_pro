"""Yeelight Pro HTTP client helper functions."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Mapping

from ..const import DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE
from .client_paths import paginated_path, product_schema_path
from .exceptions import TokenExpiredError
from .schema_cache import product_id_from_mapping

RequestCallable = Callable[..., Awaitable[dict[str, Any]]]


async def get_paginated_rows(
    request: RequestCallable,
    path_prefix: str,
    *,
    page_size: int,
) -> list[dict[str, Any]]:
    """读取返回 ``data.rows`` / ``data.total`` 的分页列表."""
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        response = await request("GET", paginated_path(path_prefix, page=page, page_size=page_size))
        data = response.get("data", {})
        page_rows = list_result(data)
        total = int_or_none(data.get("total"))

        rows.extend(page_rows)

        if not page_rows or (total is not None and len(rows) >= total):
            break

        page += 1

    return rows


async def get_product_schemas(
    request: RequestCallable,
    product_ids: list[int],
) -> dict[int, dict[str, Any]]:
    """按批次读取产品规格，并按 product id 索引."""
    schemas: dict[int, dict[str, Any]] = {}
    for i in range(0, len(product_ids), DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE):
        batch = product_ids[i:i + DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE]

        response = await _request_product_schema_batch(request, batch)

        data = response.get("data", {})
        for schema in data.get("schemas", []):
            pid = product_id_from_mapping(schema)
            if pid is not None:
                schemas[pid] = schema

    return schemas


async def _request_product_schema_batch(
    request: RequestCallable,
    product_ids: list[int],
) -> dict[str, Any]:
    """读取产品 schema；私有部署未授权公开端点时重试认证请求."""
    path = product_schema_path(product_ids)
    try:
        return await request("GET", path, with_auth=False)
    except TokenExpiredError:
        return await request("GET", path, with_auth=True)


def int_or_none(value: Any) -> int | None:
    """把 Open API 可能返回的字符串数字转为 int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def list_result(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """读取开放平台常见列表字段，优先兼容公开文档的 result."""
    rows = data.get("result")
    if rows is None:
        rows = data.get("rows")
    if rows is None:
        rows = data.get("list")
    if rows is None:
        rows = data.get("gateways")
    return rows if isinstance(rows, list) else []


def control_properties_body(
    *,
    command: str,
    duration: int | None = None,
    delay: int | None = None,
    index: int | None = None,
    category: str | None = None,
    params: dict[str, Any] | None = None,
    properties: list[str] | None = None,
) -> dict[str, Any]:
    """构造开放平台属性控制 body."""
    command_params: list[dict[str, Any]] = []
    if params is not None:
        command_params.extend(
            {"propName": prop_name, "value": value}
            for prop_name, value in params.items()
        )
    if properties is not None:
        command_params.extend({"propName": prop_name} for prop_name in properties)

    body: dict[str, Any] = {
        "command": command,
        "params": command_params,
    }
    _add_optional_control_fields(
        body,
        duration=duration,
        delay=delay,
        index=index,
        category=category,
    )
    return body


def control_property_body(
    *,
    command: str,
    value: Any | None = None,
    duration: int | None = None,
    delay: int | None = None,
    index: int | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """构造开放平台单节点单属性控制 body."""
    body: dict[str, Any] = {"command": command}
    if value is not None:
        body["value"] = value
    _add_optional_control_fields(
        body,
        duration=duration,
        delay=delay,
        index=index,
        category=category,
    )
    return body


def control_nodes_property_body(
    *,
    resource_ids: list[int | str],
    command: str,
    value: Any | None = None,
    duration: int | None = None,
    delay: int | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """构造开放平台多节点单属性控制 body."""
    body: dict[str, Any] = {
        "resIds": resource_ids,
        "command": command,
    }
    if value is not None:
        body["value"] = value
    _add_optional_control_fields(
        body,
        duration=duration,
        delay=delay,
        index=None,
        category=category,
    )
    return body


def _add_optional_control_fields(
    body: dict[str, Any],
    *,
    duration: int | None,
    delay: int | None,
    index: int | None,
    category: str | None,
) -> None:
    """追加开放平台属性控制通用可选字段."""
    if duration is not None:
        body["duration"] = duration
    if delay is not None:
        body["delay"] = delay
    if index is not None:
        body["index"] = index
    if category is not None:
        body["category"] = category


def read_properties_body(
    properties: list[str],
    *,
    index: int | None = None,
) -> dict[str, Any]:
    """构造开放平台单节点多属性读取 body."""
    body: dict[str, Any] = {"propNames": properties}
    if index is not None:
        body["index"] = index
    return body


def read_nodes_property_body(resource_ids: list[int | str]) -> dict[str, Any]:
    """构造开放平台多节点单属性读取 body."""
    return {"resIds": resource_ids}


def read_nodes_properties_body(
    resource_ids: list[int | str],
    properties: list[str],
) -> dict[str, Any]:
    """构造开放平台多节点多属性读取 body."""
    return {
        "resIds": resource_ids,
        "properties": properties,
    }
