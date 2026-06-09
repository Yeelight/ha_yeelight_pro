"""Coordinator topology-generation regression tests."""
from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator

from .coordinator_helpers import _client_with_payloads, _lamp_schema


@pytest.mark.asyncio
async def test_topology_generation_ignores_state_only_changes(
    hass: HomeAssistant,
) -> None:
    """轮询状态变化不应重复触发实体注册表同步."""
    client = _client_with_payloads(
        devices=[
            [
                {
                    "id": 1,
                    "name": "Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "o", "value": True},
                        {"propId": "l", "value": 20},
                    ],
                }
            ],
            [
                {
                    "id": 1,
                    "name": "Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "o", "value": False},
                        {"propId": "l", "value": 80},
                    ],
                }
            ],
        ]
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    first_generation = coordinator.topology_generation
    await coordinator._async_update_data()

    assert first_generation == 1
    assert coordinator.topology_generation == first_generation
    assert coordinator.devices[1]["params"]["l"] == 80


@pytest.mark.asyncio
async def test_schema_aware_topology_generation_ignores_state_only_changes(
    hass: HomeAssistant,
) -> None:
    """schema-aware canonical 分支同样不能因状态值变化递增拓扑代数."""
    schema = _lamp_schema()
    client = _client_with_payloads(
        devices=[
            [
                {
                    "id": 1,
                    "name": "Schema Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "o", "value": True},
                        {"propId": "p", "value": True},
                        {"propId": "l", "value": 20},
                    ],
                }
            ],
            [
                {
                    "id": 1,
                    "name": "Schema Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "o", "value": False},
                        {"propId": "p", "value": False},
                        {"propId": "l", "value": 80},
                    ],
                }
            ],
        ],
        product_schemas={100: schema},
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    first_generation = coordinator.topology_generation
    await coordinator._async_update_data()

    assert first_generation == 1
    assert coordinator.topology_generation == first_generation
    assert coordinator.devices[1]["ha_device_instance"]["components"][0]["state"] == {
        "p": False,
        "l": 80,
    }


@pytest.mark.asyncio
async def test_topology_generation_changes_when_entities_change(
    hass: HomeAssistant,
) -> None:
    """新增会生成实体的拓扑项时才递增 topology generation."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
        ],
        scenes=[
            [],
            [{"id": "scene_1", "name": "Evening"}],
        ],
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    first_generation = coordinator.topology_generation
    await coordinator._async_update_data()

    assert first_generation == 1
    assert coordinator.topology_generation == 2
    summary = coordinator.topology_diff_summary
    assert summary.added["scenes"] == 1
    assert summary.total_added == 1
    assert summary.total_removed == 0
    assert summary.total_metadata_changed == 0


@pytest.mark.asyncio
async def test_topology_generation_tracks_area_changes(
    hass: HomeAssistant,
) -> None:
    """area 节点变化应进入 topology snapshot/diff."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
        ],
        areas=[
            [],
            [{"id": "area-secret", "name": "Area 1"}],
        ],
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    assert coordinator.areas == [{"id": "area-secret", "name": "Area 1"}]
    assert coordinator.topology_generation == 2
    summary = coordinator.topology_diff_summary
    assert summary.added["areas"] == 1
    assert summary.total_added == 1
