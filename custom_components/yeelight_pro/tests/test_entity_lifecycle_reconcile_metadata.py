"""Tests for Yeelight Pro active registry metadata reconciliation."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.const import EntityCategory
import pytest

from custom_components.yeelight_pro.entity_lifecycle import (
    async_reconcile_entity_registry,
    entity_registry_reconcile_diagnostics,
)
from custom_components.yeelight_pro.identity import entry_identity_scope, scoped_entity_unique_id

from .entity_lifecycle_helpers import (
    FakeEntityRegistry,
    lifecycle_coordinator,
    patch_entity_registry,
    reconcile_diagnostics,
    registry_entry,
)


@pytest.mark.asyncio
async def test_reconcile_refreshes_active_registry_original_name_and_icon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """active 实体应刷新集成自有原始名称/图标，修复旧 registry 的裸数字通道名."""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_relay-1_switch_1",
            entity_id="switch.relay_1",
            domain="switch",
            original_name="1",
            original_icon=None,
            has_entity_name=False,
        )
    ])
    coordinator = lifecycle_coordinator(
        data={
            1: {
                "device_id": "relay-1",
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {"1-p": True},
            }
        }
    )
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {"yeelight_pro_relay-1_switch_1"}
    assert registry.updated_entities == [
        (
            "switch.relay_1",
            {
                "original_name": "回路 1",
                "original_icon": "mdi:light-switch",
                "has_entity_name": True,
                "disabled_by": None,
            },
        )
    ]
    assert registry.entries[0].original_name == "回路 1"
    assert registry.entries[0].original_icon == "mdi:light-switch"
    assert registry.entries[0].has_entity_name is True
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=1,
        registry_entries=1,
        stale=0,
        pending_stale=0,
        metadata_updated=1,
    )


@pytest.mark.asyncio
async def test_reconcile_refreshes_static_house_select_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """house-level select 旧 registry 条目也必须回填友好名称和图标."""
    scope = entry_identity_scope({}, 429392)
    room_uid = scoped_entity_unique_id(scope, "select", "room")
    group_uid = scoped_entity_unique_id(scope, "select", "group")
    scene_uid = scoped_entity_unique_id(scope, "select", "scene")
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id=room_uid,
                entity_id="select.yeelight_pro_429392",
                domain="select",
                original_name=None,
                original_icon=None,
                has_entity_name=None,
            ),
            registry_entry(
                unique_id=group_uid,
                entity_id="select.yeelight_pro_429392_2",
                domain="select",
                original_name=None,
                original_icon=None,
                has_entity_name=None,
            ),
            registry_entry(
                unique_id=scene_uid,
                entity_id="select.yeelight_pro_429392_3",
                domain="select",
                original_name=None,
                original_icon=None,
                has_entity_name=None,
            ),
        ]
    )
    coordinator = lifecycle_coordinator()
    coordinator.house_id = 429392
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {
        room_uid,
        group_uid,
        scene_uid,
    }
    assert registry.updated_entities == [
        (
            "select.yeelight_pro_429392",
            {
                "original_icon": "mdi:floor-plan",
                "entity_category": EntityCategory.CONFIG,
                "has_entity_name": True,
                "disabled_by": None,
            },
        ),
        (
            "select.yeelight_pro_429392_2",
            {
                "original_icon": "mdi:lightbulb-group",
                "entity_category": EntityCategory.CONFIG,
                "has_entity_name": True,
                "disabled_by": None,
            },
        ),
        (
            "select.yeelight_pro_429392_3",
            {
                "original_icon": "mdi:palette",
                "entity_category": EntityCategory.CONFIG,
                "has_entity_name": True,
                "disabled_by": None,
            },
        ),
    ]
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=3,
        registry_entries=3,
        stale=0,
        pending_stale=0,
        metadata_updated=3,
    )


@pytest.mark.asyncio
async def test_reconcile_does_not_refresh_removed_scene_domain_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同 unique_id 下只刷新 active button，旧 scene 平台继续走 stale 审计."""
    scope = entry_identity_scope({}, 0)
    scene_uid = scoped_entity_unique_id(scope, "scene", "scene_1")
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id=scene_uid,
                entity_id="scene.old_scene",
                domain="scene",
                original_name="旧场景",
                original_icon="mdi:home",
            ),
            registry_entry(
                unique_id=scene_uid,
                entity_id="button.scene_1",
                domain="button",
                original_name=None,
                original_icon=None,
                has_entity_name=False,
            ),
        ]
    )
    coordinator = lifecycle_coordinator(scenes=[{"id": "scene_1", "name": "回家"}])
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {scene_uid}
    assert registry.updated_entities == [
        (
            "button.scene_1",
            {
                "original_name": "回家",
                "original_icon": "mdi:palette",
                "entity_category": EntityCategory.CONFIG,
                "has_entity_name": True,
                "disabled_by": None,
            },
        )
    ]
    assert registry.entries[0].original_name == "旧场景"
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("scene", scene_uid)
    }
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=1,
        registry_entries=2,
        stale=1,
        pending_stale=1,
        metadata_updated=1,
    )


@pytest.mark.asyncio
async def test_reconcile_refreshes_active_registry_entity_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """active 诊断实体应回填 HA registry 的 entity_category。"""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_sensor-1_battery",
            entity_id="sensor.sensor_1_battery",
            domain="sensor",
            original_name="电量",
            has_entity_name=True,
            entity_category=None,
        )
    ])
    coordinator = lifecycle_coordinator(
        data={
            1: {
                "device_id": "sensor-1",
                "category": "contact_sensor",
                "online": True,
                "params": {"bl": 86},
            }
        }
    )
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {"yeelight_pro_sensor-1_battery"}
    assert registry.updated_entities == [
        (
            "sensor.sensor_1_battery",
            {
                "entity_category": EntityCategory.DIAGNOSTIC,
                "disabled_by": None,
            },
        )
    ]
    assert registry.entries[0].entity_category == EntityCategory.DIAGNOSTIC


@pytest.mark.asyncio
async def test_reconcile_clears_stale_active_registry_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """单主实体应清掉旧 original_name，使 HA 使用设备名作为主显示名."""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_light-1_light",
            entity_id="light.light_1",
            domain="light",
            original_name="照明",
            original_icon="mdi:home",
            entity_category=EntityCategory.CONFIG,
            has_entity_name=True,
        )
    ])
    coordinator = lifecycle_coordinator(
        data={
            1: {
                "device_id": "light-1",
                "category": "light",
                "type": "light",
                "online": True,
                "params": {"p": True, "l": 80},
            }
        }
    )
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {"yeelight_pro_light-1_light"}
    assert registry.updated_entities == [
        (
            "light.light_1",
            {
                "original_name": None,
                "original_icon": "mdi:lightbulb",
                "entity_category": None,
                "disabled_by": None,
            },
        )
    ]
    assert registry.entries[0].original_name is None
    assert registry.entries[0].entity_category is None
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=1,
        registry_entries=1,
        stale=0,
        pending_stale=0,
        metadata_updated=1,
    )
