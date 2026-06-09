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
    registry_entry,
)


@pytest.mark.asyncio
async def test_reconcile_marks_stale_registry_entry_pending_without_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """首次发现 stale entry 只记录 pending，不立即删除."""
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
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("scene", "yeelight_pro_scene_stale")
    }
    assert entity_registry_reconcile_diagnostics(coordinator) == {
        "active": 0,
        "registry_entries": 1,
        "stale": 1,
        "pending_stale": 1,
        "disabled": 0,
    }


@pytest.mark.asyncio
async def test_reconcile_keeps_same_stale_registry_entry_on_second_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """自动 reconciliation 不删除 stale entry，显式 cleanup service 才能禁用."""
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
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("scene", "yeelight_pro_scene_stale")
    }
    assert entity_registry_reconcile_diagnostics(coordinator) == {
        "active": 0,
        "registry_entries": 1,
        "stale": 1,
        "pending_stale": 1,
        "disabled": 0,
    }


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
    assert entity_registry_reconcile_diagnostics(coordinator) == {
        "active": 0,
        "registry_entries": 1,
        "stale": 0,
        "pending_stale": 0,
        "disabled": 0,
    }


@pytest.mark.asyncio
async def test_reconcile_keeps_same_unique_id_in_other_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """相同 unique_id 在不同 HA domain 下必须作为不同实体保留."""
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
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == set()
    assert entity_registry_reconcile_diagnostics(coordinator) == {
        "active": 2,
        "registry_entries": 2,
        "stale": 0,
        "pending_stale": 0,
        "disabled": 0,
    }


@pytest.mark.asyncio
async def test_reconcile_clears_pending_when_stale_registry_entry_is_active_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stale entry 重新出现在 active keys 后清空 pending 状态."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_scene_restored",
                entity_id="scene.restored",
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
    coordinator.scenes = [{"id": "restored"}]

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {"yeelight_pro_scene_restored"}
    assert registry.removed_entity_ids == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == set()
    assert entity_registry_reconcile_diagnostics(coordinator) == {
        "active": 2,
        "registry_entries": 1,
        "stale": 0,
        "pending_stale": 0,
        "disabled": 0,
    }


@pytest.mark.asyncio
async def test_reconcile_keeps_active_experimental_vacuum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """active vacuum registry entry 不应被两阶段 stale 机制误删."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_88_vacuum",
                entity_id="vacuum.robot",
                domain="vacuum",
            )
        ]
    )
    coordinator = lifecycle_coordinator(
        data={
            88: {
                "device_id": 88,
                "category": "other",
                "type": "vacuum",
                "online": True,
                "params": {"status": "idle", "battery": 80},
            }
        }
    )
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert "yeelight_pro_88_vacuum" in active_unique_ids
    assert registry.removed_entity_ids == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == set()
    assert entity_registry_reconcile_diagnostics(coordinator) == {
        "active": 3,
        "registry_entries": 1,
        "stale": 0,
        "pending_stale": 0,
        "disabled": 0,
    }
