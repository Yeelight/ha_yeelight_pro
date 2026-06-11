"""Tests for Yeelight Pro entity-registry display-name reconciliation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

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
async def test_reconcile_marks_extra_double_switch_channel_stale_and_updates_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """双键开关残留第三路应进入 stale，旧一键二键名称应刷新为左/右键."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_311884747_switch_1",
                entity_id="switch.kitchen_left",
                domain="switch",
                original_name="一键",
            ),
            registry_entry(
                unique_id="yeelight_pro_311884747_switch_2",
                entity_id="switch.kitchen_right",
                domain="switch",
                original_name="二键",
            ),
            registry_entry(
                unique_id="yeelight_pro_311884747_switch_3",
                entity_id="switch.kitchen_stale",
                domain="switch",
                original_name="三键",
            ),
        ]
    )
    coordinator = lifecycle_coordinator(
        data={
            311884747: {
                "device_id": "311884747",
                "id": 311884747,
                "name": "厨房双键开关",
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {"1-p": True, "2-p": False, "3-p": True},
            }
        }
    )
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {
        "yeelight_pro_311884747_switch_1",
        "yeelight_pro_311884747_switch_2",
    }
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("switch", "yeelight_pro_311884747_switch_3")
    }
    assert registry.updated_entities == [
        (
            "switch.kitchen_left",
            {"original_name": "左键", "original_icon": "mdi:light-switch", "disabled_by": None},
        ),
        (
            "switch.kitchen_right",
            {"original_name": "右键", "original_icon": "mdi:light-switch", "disabled_by": None},
        ),
    ]
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=2,
        registry_entries=3,
        stale=1,
        pending_stale=1,
        metadata_updated=2,
    )


@pytest.mark.asyncio
async def test_reconcile_clears_generated_single_light_original_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """单 light 主实体旧照明名称应清空，让 HA 使用设备名显示."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_311884723_light",
                entity_id="light.bathroom_mirror",
                domain="light",
                original_name="照明",
                original_icon="mdi:lightbulb",
            ),
        ]
    )
    coordinator = lifecycle_coordinator(
        data={
            311884723: {
                "device_id": "311884723",
                "id": 311884723,
                "name": "卫生间镜前灯",
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

    assert active_unique_ids == {"yeelight_pro_311884723_light"}
    assert registry.updated_entities == [
        (
            "light.bathroom_mirror",
            {"original_name": None, "disabled_by": None},
        )
    ]
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=1,
        registry_entries=1,
        stale=0,
        pending_stale=0,
        metadata_updated=1,
    )
