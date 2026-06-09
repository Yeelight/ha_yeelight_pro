"""Coordinator topology-diff regression tests."""
from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator

from .coordinator_helpers import _client_with_payloads


@pytest.mark.asyncio
async def test_topology_diff_tracks_area_room_membership_changes(
    hass: HomeAssistant,
) -> None:
    """区域包含房间变化应归类为 area metadata_changed."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
        ],
        areas=[
            [{"id": "area-secret", "name": "Area 1", "roomIds": [10]}],
            [{"id": "area-secret", "name": "Area 1", "roomIds": [10, 11]}],
        ],
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    summary = coordinator.topology_diff_summary
    assert coordinator.topology_generation == 2
    assert summary.metadata_changed["areas"] == 1
    assert summary.total_metadata_changed == 1
    assert summary.total_added == 0
    assert summary.total_removed == 0


@pytest.mark.asyncio
async def test_topology_diff_ignores_area_room_membership_order(
    hass: HomeAssistant,
) -> None:
    """区域房间成员顺序变化不应误报 metadata_changed."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
        ],
        areas=[
            [{"id": "area-secret", "name": "Area 1", "roomIds": [10, 11]}],
            [{"id": "area-secret", "name": "Area 1", "roomIds": [11, 10]}],
        ],
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    first_generation = coordinator.topology_generation
    await coordinator._async_update_data()

    summary = coordinator.topology_diff_summary
    assert first_generation == 1
    assert coordinator.topology_generation == 1
    assert summary.metadata_changed["areas"] == 0
    assert summary.total_changes == 0


@pytest.mark.asyncio
async def test_topology_diff_classifies_removed_devices(
    hass: HomeAssistant,
) -> None:
    """移除拓扑项时应输出脱敏 removed 分类摘要."""
    client = _client_with_payloads(
        devices=[
            [
                {"id": 1, "name": "Lamp A", "category": "light", "pid": 100},
                {"id": 2, "name": "Lamp B", "category": "light", "pid": 100},
            ],
            [{"id": 1, "name": "Lamp A", "category": "light", "pid": 100}],
        ]
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    summary = coordinator.topology_diff_summary
    assert coordinator.topology_generation == 2
    assert summary.removed["devices"] == 1
    assert summary.total_removed == 1
    assert summary.total_added == 0
    assert summary.total_metadata_changed == 0


@pytest.mark.asyncio
async def test_topology_diff_classifies_metadata_changes(
    hass: HomeAssistant,
) -> None:
    """设备名称、房间或组件拓扑变化应归类为 metadata_changed."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
            [{"id": 1, "name": "Renamed Lamp", "category": "light", "pid": 100}],
        ]
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    summary = coordinator.topology_diff_summary
    assert coordinator.topology_generation == 2
    assert summary.metadata_changed["devices"] == 1
    assert summary.total_metadata_changed == 1
    assert summary.total_added == 0
    assert summary.total_removed == 0


@pytest.mark.asyncio
async def test_topology_diff_is_empty_for_state_only_changes(
    hass: HomeAssistant,
) -> None:
    """状态轮询变化不应留下误导性的 topology diff."""
    client = _client_with_payloads(
        devices=[
            [
                {
                    "id": 1,
                    "name": "Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "p", "value": True},
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
                        {"propId": "p", "value": False},
                        {"propId": "l", "value": 80},
                    ],
                }
            ],
        ]
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    summary = coordinator.topology_diff_summary
    assert coordinator.topology_generation == 1
    assert summary.total_changes == 0
    assert summary.as_dict()["current_generation"] == 1
