"""Yeelight Pro HTTP client helper functions."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Awaitable, Callable, Mapping

from ..const import DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE
from .client_paths import paginated_path, product_schema_path
from .exceptions import CommandError, TokenExpiredError, YeelightProError
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

        responses = await _request_product_schema_batch(request, batch)
        batch_schemas: dict[int, dict[str, Any]] = {}
        for schema in _merged_product_schema_rows(responses):
            pid = product_id_from_mapping(schema)
            if pid is not None:
                batch_schemas[pid] = schema
        schemas.update(batch_schemas)

    return schemas


async def _request_product_schema_batch(
    request: RequestCallable,
    product_ids: list[int],
) -> list[Mapping[str, Any]]:
    """读取产品 schema；优先合并 v1/v2 以最大化能力覆盖."""
    responses: list[Mapping[str, Any]] = []
    primary_error: YeelightProError | None = None

    try:
        responses.append(await _request_product_schema_batch_v1(request, product_ids))
    except CommandError as err:
        if "404" not in str(err):
            raise
        primary_error = err

    try:
        responses.append(await _request_product_schema_batch_v2(request, product_ids))
    except YeelightProError:
        if not responses:
            raise

    if not responses and primary_error is not None:
        raise primary_error
    return responses


async def _request_product_schema_batch_v1(
    request: RequestCallable,
    product_ids: list[int],
) -> dict[str, Any]:
    """读取 v1 产品 schema；私有部署未授权公开端点时重试认证请求."""
    path = product_schema_path(product_ids)
    try:
        return await request("GET", path, with_auth=False)
    except TokenExpiredError:
        return await request("GET", path, with_auth=True)


async def _request_product_schema_batch_v2(
    request: RequestCallable,
    product_ids: list[int],
) -> dict[str, Any]:
    """读取 v2 产品 schema；公开端点失败为认证场景时再携带 token."""
    path = product_schema_path(product_ids, version="v2")
    try:
        return await request("GET", path, with_auth=False)
    except TokenExpiredError:
        return await request("GET", path, with_auth=True)


def _merged_product_schema_rows(
    responses: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """合并多个产品 schema 响应中相同 PID 的 schema."""
    schemas: dict[int, dict[str, Any]] = {}
    for response in responses:
        for schema in _product_schema_rows(response):
            pid = product_id_from_mapping(schema)
            if pid is None:
                continue
            existing = schemas.get(pid)
            schemas[pid] = (
                schema
                if existing is None
                else _merge_product_schema(existing, schema)
            )
    return list(schemas.values())


def _product_schema_rows(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    """读取 v1/v2 产品 schema 响应中的 schema 列表."""
    data = response.get("data")
    if isinstance(data, list):
        return [dict(item) for item in data if isinstance(item, Mapping)]
    if isinstance(data, Mapping):
        schemas = data.get("schemas")
        if isinstance(schemas, list):
            return [dict(item) for item in schemas if isinstance(item, Mapping)]
    return []


def _merge_product_schema(
    base: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    """保守合并同一 PID 的 v1/v2 schema，优先补字段而非覆盖."""
    merged = dict(base)
    for key, value in overlay.items():
        if _empty_schema_value(value):
            continue
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = _merge_product_schema(current, value)
        elif isinstance(current, list) and isinstance(value, list):
            merged[key] = _merge_schema_list(current, value)
        elif _empty_schema_value(current):
            merged[key] = value
    return merged


def _merge_schema_list(base: list[Any], overlay: list[Any]) -> list[Any]:
    """按稳定身份合并 schema 列表，保留原顺序并追加新增项."""
    merged = list(base)
    indexes: dict[tuple[Any, ...], int] = {}
    for index, item in enumerate(merged):
        identity = _schema_list_item_identity(item)
        if identity is not None:
            indexes[identity] = index

    for item in overlay:
        identity = _schema_list_item_identity(item)
        if identity is None:
            if item not in merged:
                merged.append(item)
            continue
        existing_index = indexes.get(identity)
        if existing_index is None:
            indexes[identity] = len(merged)
            merged.append(item)
            continue
        existing = merged[existing_index]
        if isinstance(existing, Mapping) and isinstance(item, Mapping):
            merged[existing_index] = _merge_product_schema(existing, item)
    return merged


def _schema_list_item_identity(item: Any) -> tuple[Any, ...] | None:
    """提取 schema 列表元素身份，用于跨版本去重合并."""
    if not isinstance(item, Mapping):
        return None
    for key in ("propId", "eventId", "actionName", "code"):
        if item.get(key) is not None:
            return (key, str(item.get(key)))
    if item.get("cid") is not None or item.get("index") is not None:
        return (
            "component",
            item.get("cid"),
            item.get("index"),
        )
    if item.get("id") is not None:
        return ("id", str(item.get("id")))
    if item.get("name") is not None or item.get("category") is not None:
        return (
            "named",
            str(item.get("type")),
            str(item.get("category")),
            str(item.get("name")),
        )
    return None


def _empty_schema_value(value: Any) -> bool:
    """判断 schema 字段是否缺省，供跨版本补全使用."""
    return value is None or value == "" or value == [] or value == {}


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
