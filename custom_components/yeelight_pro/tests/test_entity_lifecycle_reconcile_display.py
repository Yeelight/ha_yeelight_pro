"""Tests for Yeelight Pro entity-registry display-name reconciliation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_PRIVATE,
)
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
async def test_reconcile_marks_extra_catalog_double_switch_channel_stale_and_updates_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """官方双键产品残留第三路应进入 stale，旧一键二键名称应刷新为左/右键."""
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
                "name": "厨房开关",
                "pid": 854018,
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
async def test_reconcile_updates_four_key_wireless_switch_names_to_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """四键无线开关旧“回路”名称应刷新为物模型输入按键语义。"""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id=f"yeelight_pro_40266116_switch_{index}",
                entity_id=f"switch.four_key_{index}",
                domain="switch",
                original_name=f"回路 {index}",
            )
            for index in range(1, 5)
        ]
    )
    coordinator = lifecycle_coordinator(
        data={
            40266116: {
                "device_id": "40266116",
                "id": 40266116,
                "name": "四键",
                "pid": 854041,
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {
                    "1-sp": True,
                    "2-sp": False,
                    "3-sp": True,
                    "4-sp": False,
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
        f"yeelight_pro_40266116_switch_{index}" for index in range(1, 5)
    }
    assert registry.updated_entities == [
        (
            f"switch.four_key_{index}",
            {
                "original_name": f"按键 {index}",
                "original_icon": "mdi:light-switch",
                "disabled_by": None,
            },
        )
        for index in range(1, 5)
    ]
    assert [entry.original_name for entry in registry.entries] == [
        "按键 1",
        "按键 2",
        "按键 3",
        "按键 4",
    ]
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=4,
        registry_entries=4,
        stale=0,
        pending_stale=0,
        metadata_updated=4,
    )


@pytest.mark.asyncio
async def test_reconcile_disables_legacy_private_endpoint_alias_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """私有部署 URL 归一化遗留的旧 scope 实体应自动禁用，避免设备页重复."""
    active_scope = "private_endpoint_625450e28ea30c27_house_99529"
    legacy_scope = "private_endpoint_1ba60251fd570476_house_99529"
    active_entries = [
        registry_entry(
            unique_id=_scoped_four_key_uid(active_scope, index),
            entity_id=f"switch.four_key_key_{index}",
            domain="switch",
            original_name=f"按键 {index}",
        )
        for index in range(1, 5)
    ]
    legacy_entries = [
        registry_entry(
            unique_id=_scoped_four_key_uid(legacy_scope, index),
            entity_id=f"switch.four_key_loop_{index}",
            domain="switch",
            original_name=f"回路 {index}",
        )
        for index in range(1, 5)
    ]
    other_entry = registry_entry(
        unique_id=_scoped_four_key_uid(legacy_scope, 99),
        entity_id="switch.other_entry_loop",
        domain="switch",
        config_entry_id="entry_other",
        original_name="回路 99",
    )
    registry = FakeEntityRegistry(
        active_entries,
        global_entries=[*legacy_entries, other_entry],
    )
    coordinator = lifecycle_coordinator(
        data={
            40266116: {
                "_yeelight_identity_scope": active_scope,
                "device_id": "40266116",
                "id": 40266116,
                "name": "四键",
                "category": "relay_switch",
                "type": "switch",
                "online": True,
                "params": {
                    "1-p": True,
                    "1-sp": True,
                    "2-p": False,
                    "2-sp": False,
                    "3-p": False,
                    "3-sp": False,
                    "4-p": False,
                    "4-sp": False,
                },
                "subDeviceList": [
                    {
                        "index": index,
                        "name": "wireless switch channel",
                        "category": "relay_switch",
                    }
                    for index in range(1, 5)
                ],
            }
        }
    )
    coordinator.house_id = 99529
    coordinator.entry_data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://api-test.yeedev.com",
        CONF_HOUSE_ID: 99529,
    }
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    four_key_unique_ids = {
        _scoped_four_key_uid(active_scope, index)
        for index in range(1, 5)
    }
    assert four_key_unique_ids.issubset(active_unique_ids)
    disabled_updates = [
        update
        for update in registry.updated_entities
        if update[0].startswith("switch.four_key_loop_")
    ]
    assert disabled_updates == [
        (f"switch.four_key_loop_{index}", {"disabled_by": "integration"})
        for index in range(1, 5)
    ]
    assert all(entry.disabled_by == "integration" for entry in legacy_entries)
    assert other_entry.disabled_by is None
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=7,
        registry_entries=8,
        stale=4,
        pending_stale=0,
        disabled=4,
        metadata_updated=4,
    )


def _scoped_four_key_uid(scope: str, index: int) -> str:
    """Return the scoped unique id for the four-key switch fixture."""
    return f"yeelight_pro_{scope}_device_40266116_switch_{index}"


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
