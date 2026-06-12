"""Product-catalog-backed property hydration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.core.property_hydration import (
    async_hydrate_device_properties,
)


@pytest.mark.asyncio
async def test_hydration_uses_product_catalog_properties_for_pid_only_switch() -> None:
    """只有 pid 的多键开关应按产品构成补拉官方无线开关通道属性."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {"code": "200", "data": {}}

    await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[
            {
                "id": 85401801,
                "name": "双键开关",
                "category": "light",
                "pid": 854018,
            }
        ],
        product_schemas={},
    )

    kwargs = client.read_nodes_properties.await_args.kwargs
    assert kwargs["resource_ids"] == [85401801]
    assert {
        "l",
        "sp",
        "slisaon",
        "slisaon_rdy",
        "sbp",
        "li",
        "run_speed",
        "run_speed_rdy",
    } <= set(kwargs["properties"])


@pytest.mark.asyncio
async def test_hydration_uses_product_catalog_properties_for_contact_sensor() -> None:
    """门窗传感器 pid 应补拉接触、防拆和电池类官方属性."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {"code": "200", "data": {}}

    await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[
            {
                "id": 852249601,
                "name": "门窗传感器",
                "category": "light",
                "pid": 8522496,
            }
        ],
        product_schemas={},
    )

    kwargs = client.read_nodes_properties.await_args.kwargs
    assert {"dc", "alm", "bl", "bc", "bcg"} <= set(kwargs["properties"])
