"""Tests for Yeelight Pro entity-registry stale reconciliation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.yeelight_pro import entity_lifecycle
from custom_components.yeelight_pro.entity_lifecycle import (
    async_reconcile_entity_registry,
    entity_registry_reconcile_diagnostics,
)

from .entity_lifecycle_helpers import (
    FakeEntityRegistry,
    lifecycle_coordinator,
    patch_entity_registry,
    reconcile_diagnostics,
    registry_entry,
)


@pytest.mark.asyncio
async def test_reconcile_marks_stale_registry_entry_pending_without_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """发现 stale entry 时只记录 pending，不自动禁用或删除 registry 数据."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_scene_stale",
                entity_id="scene.stale",
                domain="scene",
            )
        ]
    )
    coordinator = lifecycle_coordinator()
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == set()
    assert registry.removed_entity_ids == []
    assert registry.updated_entities == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("scene", "yeelight_pro_scene_stale")
    }
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=0, registry_entries=1, stale=1, pending_stale=1
    )


@pytest.mark.asyncio
async def test_reconcile_keeps_same_stale_registry_entry_on_second_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """第二轮仍只保留 pending stale，不自动禁用或删除."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_scene_stale",
                entity_id="scene.stale",
                domain="scene",
            )
        ]
    )
    coordinator = lifecycle_coordinator()
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )
    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert registry.removed_entity_ids == []
    assert registry.updated_entities == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("scene", "yeelight_pro_scene_stale")
    }
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=0, registry_entries=1, stale=1, pending_stale=1
    )


@pytest.mark.asyncio
async def test_reconcile_treats_filtered_device_entities_as_stale_without_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """设备导入过滤可进入 stale 判断，但自动 reconcile 不禁用实体."""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_blocked-light_light",
            entity_id="light.blocked",
            domain="light",
        )
    ])
    coordinator = lifecycle_coordinator(
        data={
            1: {
                "device_id": "blocked-light",
                "category": "light",
                "type": "light",
                "online": True,
                "params": {"p": True},
            }
        },
        options={
            "device_import_filter": {
                "enabled": True,
                "exclude": {"devices": ["blocked-light"]},
            }
        },
    )
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == set()
    assert registry.removed_entity_ids == []
    assert registry.updated_entities == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("light", "yeelight_pro_blocked-light_light")
    }
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=0, registry_entries=1, stale=1, pending_stale=1
    )


@pytest.mark.asyncio
async def test_reconcile_filtered_device_without_registry_entry_does_not_disable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """被过滤的新设备没有 registry 条目时，不应产生自动禁用动作."""
    registry = FakeEntityRegistry([])
    coordinator = lifecycle_coordinator(
        data={
            1: {
                "device_id": "blocked-light",
                "category": "light",
                "type": "light",
                "online": True,
                "params": {"p": True},
            }
        },
        options={
            "device_import_filter": {
                "enabled": True,
                "exclude": {"devices": ["blocked-light"]},
            }
        },
    )
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == set()
    assert registry.removed_entity_ids == []
    assert registry.updated_entities == []
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=0, registry_entries=0, stale=0, pending_stale=0
    )


@pytest.mark.asyncio
async def test_reconcile_preserves_user_disabled_stale_registry_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户主动禁用的 stale entry 不应被自动清理."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_scene_user_disabled",
                entity_id="scene.user_disabled",
                domain="scene",
                disabled_by=entity_lifecycle.er.RegistryEntryDisabler.USER,
            )
        ]
    )
    coordinator = lifecycle_coordinator()
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )
    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert registry.removed_entity_ids == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == set()
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=0, registry_entries=1, stale=0, pending_stale=0
    )


@pytest.mark.asyncio
async def test_reconcile_marks_removed_scene_domain_stale_when_button_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """删除原生 scene 平台后，同 unique_id 的 button 保留，scene 进入 stale."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_scene_scene_1",
                entity_id="scene.duplicate",
                domain="scene",
            ),
            registry_entry(
                unique_id="yeelight_pro_scene_scene_1",
                entity_id="button.duplicate",
                domain="button",
                original_name="情景 scene_1",
                original_icon="mdi:palette",
            ),
        ]
    )
    coordinator = lifecycle_coordinator(scenes=[{"id": "scene_1"}])
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {"yeelight_pro_scene_scene_1"}
    assert registry.removed_entity_ids == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("scene", "yeelight_pro_scene_scene_1")
    }
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=1,
        registry_entries=2,
        stale=1,
        pending_stale=1,
        metadata_updated=1,
    )


@pytest.mark.asyncio
async def test_reconcile_clears_pending_when_stale_registry_entry_is_active_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stale entry 重新出现在 active keys 后清空 pending 状态."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_scene_restored",
                entity_id="button.restored",
                domain="button",
                original_name="情景 restored",
                original_icon="mdi:palette",
            )
        ]
    )
    coordinator = lifecycle_coordinator()
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )
    coordinator.scenes = [{"id": "restored"}]

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {"yeelight_pro_scene_restored"}
    assert registry.removed_entity_ids == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == set()
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=1,
        registry_entries=1,
        stale=0,
        pending_stale=0,
        metadata_updated=1,
    )


@pytest.mark.asyncio
async def test_reconcile_preserves_active_user_disabled_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """active entry 即使重新出现，也不能覆盖用户主动禁用状态."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_scene_user_disabled_active",
                entity_id="scene.user_disabled_active",
                domain="scene",
                disabled_by=entity_lifecycle.er.RegistryEntryDisabler.USER,
            )
        ]
    )
    coordinator = lifecycle_coordinator(scenes=[{"id": "user_disabled_active"}])
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    user_disabled = entity_lifecycle.er.RegistryEntryDisabler.USER
    assert registry.updated_entities == []
    assert registry.entries[0].disabled_by == user_disabled
    assert (entity_registry_reconcile_diagnostics(coordinator) or {})["restored"] == 0
