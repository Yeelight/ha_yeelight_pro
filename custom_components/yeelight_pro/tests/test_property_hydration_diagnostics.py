"""Property hydration aggregate diagnostics tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.core.property_hydration import (
    async_hydrate_device_properties,
)
from custom_components.yeelight_pro.core.property_hydration_summary import (
    PropertyHydrationDiagnostics,
)


@pytest.mark.asyncio
async def test_hydration_reports_safe_aggregate_diagnostics() -> None:
    """补水诊断只暴露聚合计数，不记录设备 id 或属性值."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {
        "code": "200",
        "data": {
            "311930423": {
                "code": "200",
                "data": [
                    {"propId": "dc", "value": True},
                    {"propId": "alm", "value": False},
                ],
            },
        },
    }
    diagnostics = PropertyHydrationDiagnostics()

    await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[
            {
                "id": 311930423,
                "name": "玄关门磁传感器",
                "category": "light",
            }
        ],
        diagnostics=diagnostics,
    )

    assert diagnostics.as_dict() == {
        "request_groups": 1,
        "requested_devices": 1,
        "requested_property_sets": 37,
        "requested_node_properties": 37,
        "response_devices": 1,
        "response_values": 2,
        "merged_devices": 1,
        "merged_values": 2,
        "empty_response_groups": 0,
        "failed_groups": 0,
    }
