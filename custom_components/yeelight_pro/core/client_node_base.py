"""Shared Open API node client mixin helpers."""

from __future__ import annotations

from typing import Any

from ..const import DEFAULT_THING_MANAGE_PAGE_SIZE
from .client_helpers import (
    get_paginated_rows as _get_paginated_rows,
    get_product_schemas as _get_product_schemas,
)


class YeelightProNodeRequestMixin:
    """开放平台节点 mixin 的请求和分页基础能力."""

    async def _request(
        self,
        method: str,
        path: str,
        *,
        with_auth: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """由最终 HTTP client 提供实际请求实现."""
        raise NotImplementedError

    async def _get_paginated_rows(
        self,
        path_prefix: str,
        *,
        page_size: int = DEFAULT_THING_MANAGE_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        """读取返回 ``data.rows`` / ``data.total`` 的分页列表."""
        return await _get_paginated_rows(
            self._request,
            path_prefix,
            page_size=page_size,
        )

    async def get_product_schemas(
        self,
        product_ids: list[int],
    ) -> dict[int, dict[str, Any]]:
        """获取产品规格."""
        return await _get_product_schemas(self._request, product_ids)
