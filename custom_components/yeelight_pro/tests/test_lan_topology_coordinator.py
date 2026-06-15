"""Coordinator integration tests for LAN topology payloads."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    CONNECTION_MODE_LAN,
    DOMAIN,
)
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.ha_device_registry import async_sync_gateway_devices
from custom_components.yeelight_pro.identity import (
    entry_identity_scope,
    scoped_device_identifier,
    scoped_entity_unique_id,
)


@pytest.mark.asyncio
async def test_lan_topology_syncs_source_devices_and_relinks_entities(
    hass: HomeAssistant,
) -> None:
    """LAN-only 拓扑设备也必须进入 HA device registry 并回链既有实体。"""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="entry-lan")
    entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    lan_entry_data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_LAN,
        CONF_LAN_GATEWAY_IP: "127.0.0.1",
        CONF_LAN_GATEWAY_PORT: 65443,
    }
    lan_scope = entry_identity_scope(lan_entry_data, 0)
    entity_entry = entity_registry.async_get_or_create(
        "light",
        DOMAIN,
        scoped_entity_unique_id(lan_scope, "device", 1001, "light"),
        config_entry=entry,
    )
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=None,
        house_id=0,
        entry_data=lan_entry_data,
    )

    await coordinator.async_handle_lan_payload(
        {
            "id": 13812,
            "method": "gateway_post.topology",
            "nodes": [
                {"id": 201, "nt": 1, "n": "客厅"},
                {"id": 1001, "nt": 2, "type": 3, "n": "客厅灯", "roomid": 201},
            ],
        }
    )
    await async_sync_gateway_devices(hass, entry, coordinator)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, scoped_device_identifier(lan_scope, 1001))}
    )
    linked_entity = entity_registry.async_get(entity_entry.entity_id)

    assert device is not None
    assert device.name == "客厅灯"
    assert device.model == "色温灯"
    assert linked_entity is not None
    assert linked_entity.device_id == device.id
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_coordinator_applies_lan_areas_groups_scenes(
    hass: HomeAssistant,
) -> None:
    """LAN nt=1/3/4/6 应分别进入房间、区域、组和情景缓存。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=None,
        house_id=12345,
    )
    listener = MagicMock()
    remove_listener = coordinator.async_add_listener(listener)

    events = await coordinator.async_handle_lan_payload(
        {
            "id": 13813,
            "method": "gateway_post.topology",
            "nodes": [
                {"id": 201, "nt": 1, "n": "客厅", "o": True, "params": {"p": True}},
                {"id": 301, "nt": 3, "n": "一楼", "o": False, "params": {"p": False}},
                {"id": 5001, "nt": 5, "n": "绿地中央公园"},
                {"id": 1001, "nt": 2, "type": 3, "n": "客厅灯", "roomid": 201},
                {
                    "id": 3001,
                    "nt": 4,
                    "type": 1,
                    "n": "客厅灯组",
                    "o": True,
                    "params": {"p": True, "l": 80, "ct": 4000},
                },
                {"id": 4001, "nt": 6, "n": "回家", "params": {"state": "inactive"}},
            ],
        }
    )

    assert events == []
    assert coordinator.data == coordinator.devices
    assert list(coordinator.devices) == [1001]
    assert coordinator.rooms == [
        {
            "id": 201,
            "name": "客厅",
            "type": None,
            "node_type": 1,
            "online": True,
            "params": {"p": True},
        }
    ]
    assert coordinator.areas == [
        {
            "id": 301,
            "name": "一楼",
            "type": None,
            "node_type": 3,
            "online": False,
            "params": {"p": False},
        }
    ]
    assert coordinator.groups == [
        {
            "id": 3001,
            "name": "客厅灯组",
            "type": 1,
            "node_type": 4,
            "online": True,
            "params": {"p": True, "l": 80, "ct": 4000},
        }
    ]
    assert coordinator.houses == [
        {"id": 5001, "name": "绿地中央公园", "type": None, "node_type": 5}
    ]
    assert coordinator.scenes == [
        {"id": 4001, "name": "回家", "params": {"state": "inactive"}, "state": "inactive"}
    ]
    assert coordinator.topology_generation == 1
    listener.assert_called_once()
    remove_listener()
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_coordinator_merges_lan_scene_state_push(
    hass: HomeAssistant,
) -> None:
    """LAN prop 场景状态推送应合并进现有场景缓存并通知监听器。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=None,
        house_id=12345,
    )
    coordinator.scenes = [{"id": 4001, "name": "回家"}]
    listener = MagicMock()
    remove_listener = coordinator.async_add_listener(listener)

    events = await coordinator.async_handle_lan_payload(
        {
            "id": 13814,
            "method": "gateway_post.prop",
            "nodes": [
                {"id": 1001, "nt": 2, "params": {"p": True}},
            ],
            "scenes": [
                {"id": 4001, "n": "回家", "params": {"state": "active"}},
                {"id": 4002, "n": "离家", "params": {"state": "inactive"}},
            ],
        }
    )

    assert events == []
    assert coordinator.scenes == [
        {"id": 4001, "name": "回家", "state": "active", "params": {"state": "active"}},
        {"id": 4002, "name": "离家", "state": "inactive", "params": {"state": "inactive"}},
    ]
    listener.assert_called_once()
    remove_listener()
    await coordinator.async_shutdown()
