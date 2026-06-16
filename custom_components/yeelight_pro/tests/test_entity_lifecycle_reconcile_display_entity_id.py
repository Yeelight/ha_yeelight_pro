"""Generic display entity_id migration tests for registry reconciliation."""

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


def _multi_switch_light_payload() -> dict[str, object]:
    """构造私有部署常见的多路开关灯 canonical payload。"""
    return {
        "device_id": "611884747",
        "id": 611884747,
        "name": "S全面屏",
        "iot_category": "light",
        "category": "light",
        "type": "light",
        "online": True,
        "params": {"1-p": True, "2-p": False},
        "device_info": {
            "identifiers": [["yeelight_pro", "611884747"]],
            "name": "S全面屏",
            "manufacturer": "Yeelight",
            "model": "全面屏",
        },
        "ha_device_instance": {
            "device_id": "611884747",
            "name": "S全面屏",
            "online": True,
            "device_info": {
                "identifiers": [["yeelight_pro", "611884747"]],
                "name": "S全面屏",
                "manufacturer": "Yeelight",
                "model": "全面屏",
            },
            "components": [
                {
                    "component_id": "light_1",
                    "name": "switch light",
                    "desc": "开关灯",
                    "category": "switch light",
                    "available": True,
                    "state": {"p": True},
                },
                {
                    "component_id": "light_2",
                    "name": "switch light",
                    "desc": "开关灯",
                    "category": "switch light",
                    "available": True,
                    "state": {"p": False},
                },
            ],
            "extensions": {
                "component_state_keys": {
                    "light_1": {"p": "1-p"},
                    "light_2": {"p": "2-p"},
                }
            },
        },
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "model-611884747",
                "manufacturer": "Yeelight",
                "model": "全面屏",
                "category": "light",
            },
            "components": [
                {
                    "component_id": "light_1",
                    "name": "switch light",
                    "desc": "开关灯",
                    "category": "switch light",
                    "properties": [{"prop_id": "p", "access": "read_write"}],
                    "events": [],
                },
                {
                    "component_id": "light_2",
                    "name": "switch light",
                    "desc": "开关灯",
                    "category": "switch light",
                    "properties": [{"prop_id": "p", "access": "read_write"}],
                    "events": [],
                },
            ],
        },
    }


def _generic_switch_payload() -> dict[str, object]:
    """构造旧私有部署开关组件 payload。"""
    return {
        "device_id": "711884747",
        "id": 711884747,
        "name": "M1",
        "iot_category": "relay_switch",
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "params": {"1-p": True},
        "device_info": {
            "identifiers": [["yeelight_pro", "711884747"]],
            "name": "M1",
            "manufacturer": "Yeelight",
            "model": "开关面板",
        },
    }


@pytest.mark.asyncio
async def test_reconcile_renames_legacy_generic_component_entity_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """早期使用泛化组件名生成的 entity_id 应迁移为当前友好名称."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_611884747_light_2",
                entity_id="light.squan_mian_ping_kai_guan_deng",
                domain="light",
                original_name="回路 2",
                original_icon="mdi:lightbulb",
                has_entity_name=True,
            ),
            registry_entry(
                unique_id="yeelight_pro_711884747_switch_1",
                entity_id="switch.m1_kai_guan_zu_jian",
                domain="switch",
                original_name="右键",
                original_icon="mdi:light-switch",
                has_entity_name=True,
            ),
        ]
    )
    coordinator = lifecycle_coordinator(
        data={
            611884747: _multi_switch_light_payload(),
            711884747: _generic_switch_payload(),
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
            "light.squan_mian_ping_kai_guan_deng",
            {
                "new_entity_id": "light.squan_mian_ping_hui_lu_2",
                "disabled_by": None,
            },
        ),
        (
            "switch.m1_kai_guan_zu_jian",
            {
                "new_entity_id": "switch.m1_hui_lu_1",
                "original_name": "回路 1",
                "disabled_by": None,
            },
        ),
    ]
    assert registry.entries[0].entity_id == "light.squan_mian_ping_hui_lu_2"
    assert registry.entries[1].entity_id == "switch.m1_hui_lu_1"


@pytest.mark.asyncio
async def test_reconcile_preserves_user_named_generic_component_entity_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户已自定义名称时，即使 entity_id 含旧泛化组件名也不自动迁移."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_611884747_light_2",
                entity_id="light.squan_mian_ping_kai_guan_deng",
                domain="light",
                original_name="开关灯",
                original_icon="mdi:lightbulb",
                has_entity_name=True,
                name="床头阅读灯",
            ),
        ]
    )
    coordinator = lifecycle_coordinator(data={611884747: _multi_switch_light_payload()})
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert registry.updated_entities == [
        (
            "light.squan_mian_ping_kai_guan_deng",
            {
                "original_name": "回路 2",
                "disabled_by": None,
            },
        )
    ]
    assert registry.entries[0].entity_id == "light.squan_mian_ping_kai_guan_deng"
