"""I/O helpers for private push topology probes."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from custom_components.yeelight_pro.core.client import YeelightProClient  # noqa: E402
from custom_components.yeelight_pro.utils import to_int  # noqa: E402


async def safe_list(
    name: str,
    awaitable: Any,
    endpoint_errors: dict[str, str],
) -> list[dict[str, Any]]:
    """Return a list endpoint result and record failure type."""
    try:
        rows = await awaitable
    except Exception as err:
        endpoint_errors[name] = type(err).__name__
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


async def safe_mapping(
    name: str,
    awaitable: Any,
    endpoint_errors: dict[str, str],
) -> dict[int, dict[str, Any]]:
    """Return a mapping endpoint result and record failure type."""
    try:
        rows = await awaitable
    except Exception as err:
        endpoint_errors[name] = type(err).__name__
        return {}
    result: dict[int, dict[str, Any]] = {}
    if isinstance(rows, Mapping):
        for key, value in rows.items():
            numeric = to_int(key)
            if numeric is not None and isinstance(value, Mapping):
                result[numeric] = dict(value)
    return result


async def safe_house_rows(
    client: YeelightProClient,
    house_id: int,
    endpoint_errors: dict[str, str],
) -> list[dict[str, Any]]:
    """Return normalized house rows and record failure type."""
    try:
        payload = await client.get_house_snapshot(house_id)
    except Exception as err:
        endpoint_errors["house_snapshot"] = type(err).__name__
        return []
    data = payload.get("data") if isinstance(payload, Mapping) else None
    if isinstance(data, Mapping):
        return [dict(data)]
    if isinstance(data, list):
        return [dict(row) for row in data if isinstance(row, Mapping)]
    return [dict(payload)] if isinstance(payload, Mapping) else []


def digest(value: Any) -> str:
    """Return a stable, non-reversible short digest."""
    return hashlib.blake2b(str(value).encode("utf-8"), digest_size=8).hexdigest()


__all__ = ["digest", "safe_house_rows", "safe_list", "safe_mapping"]
