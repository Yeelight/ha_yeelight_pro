"""Tests for Yeelight Pro safe entity_id registry reconciliation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.yeelight_pro.entity_lifecycle import (
    async_reconcile_entity_registry,
)

from .entity_lifecycle_helpers import (
    FakeEntityRegistry,
    lifecycle_coordinator,
    patch_entity_registry,
    registry_entry,
)


@pytest.mark.asyncio
async def test_reconcile_renames_legacy_channel_entity_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """早期裸数字通道 entity_id 应迁移为设备名 + 友好通道名."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_311884747_switch_1",
                entity_id="switch.chu_fang_shuang_jian_kai_guan_1",
                domain="switch",
                original_name="1",
                original_icon=None,
                has_entity_name=True,
            )
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
                "params": {"1-p": True, "2-p": False},
                "device_info": {
                    "identifiers": [["yeelight_pro", "311884747"]],
                    "name": "厨房双键开关",
                    "manufacturer": "Yeelight",
                    "model": "双键开关",
                },
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
    assert registry.updated_entities == [
        (
            "switch.chu_fang_shuang_jian_kai_guan_1",
            {
                "new_entity_id": "switch.chu_fang_shuang_jian_kai_guan_zuo_jian",
                "original_name": "左键",
                "original_icon": "mdi:light-switch",
                "disabled_by": None,
            },
        )
    ]
    assert registry.entries[0].entity_id == (
        "switch.chu_fang_shuang_jian_kai_guan_zuo_jian"
    )


@pytest.mark.asyncio
async def test_reconcile_preserves_user_named_legacy_entity_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户已自定义名称的旧 entity_id 不应被集成自动改写."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_311884747_switch_1",
                entity_id="switch.chu_fang_shuang_jian_kai_guan_1",
                domain="switch",
                original_name="1",
                original_icon=None,
                has_entity_name=True,
                name="厨房主灯开关",
            )
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
                "params": {"1-p": True},
                "device_info": {
                    "identifiers": [["yeelight_pro", "311884747"]],
                    "name": "厨房双键开关",
                    "manufacturer": "Yeelight",
                    "model": "双键开关",
                },
            }
        }
    )
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert registry.updated_entities == [
        (
            "switch.chu_fang_shuang_jian_kai_guan_1",
            {
                "original_name": "左键",
                "original_icon": "mdi:light-switch",
                "disabled_by": None,
            },
        )
    ]
    assert registry.entries[0].entity_id == "switch.chu_fang_shuang_jian_kai_guan_1"


@pytest.mark.asyncio
async def test_reconcile_uses_global_entity_ids_for_legacy_migration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """迁移旧 entity_id 时必须避开其它 entry 已占用的全局 entity_id."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_311884747_switch_1",
                entity_id="switch.chu_fang_shuang_jian_kai_guan_1",
                domain="switch",
                original_name="1",
            )
        ],
        global_entries=[
            registry_entry(
                unique_id="other_unique_id",
                entity_id="switch.chu_fang_shuang_jian_kai_guan_zuo_jian",
                domain="switch",
            )
        ],
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
                "params": {"1-p": True},
                "device_info": {
                    "identifiers": [["yeelight_pro", "311884747"]],
                    "name": "厨房双键开关",
                    "manufacturer": "Yeelight",
                    "model": "双键开关",
                },
            }
        }
    )
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert registry.updated_entities == [
        (
            "switch.chu_fang_shuang_jian_kai_guan_1",
            {
                "new_entity_id": "switch.chu_fang_shuang_jian_kai_guan_zuo_jian_2",
                "original_name": "左键",
                "original_icon": "mdi:light-switch",
                "disabled_by": None,
            },
        )
    ]


@pytest.mark.asyncio
async def test_reconcile_keeps_metadata_cleanup_when_entity_id_migration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HA 拒绝 entity_id 迁移时，仍要清理旧 original_name/original_icon."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_311884747_switch_1",
                entity_id="switch.chu_fang_shuang_jian_kai_guan_1",
                domain="switch",
                original_name="1",
                original_icon=None,
            )
        ],
        rejected_new_entity_ids={"switch.chu_fang_shuang_jian_kai_guan_zuo_jian"},
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
                "params": {"1-p": True},
            }
        }
    )
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert registry.updated_entities == [
        (
            "switch.chu_fang_shuang_jian_kai_guan_1",
            {
                "original_name": "左键",
                "original_icon": "mdi:light-switch",
                "disabled_by": None,
            },
        )
    ]
    assert registry.entries[0].original_name == "左键"
