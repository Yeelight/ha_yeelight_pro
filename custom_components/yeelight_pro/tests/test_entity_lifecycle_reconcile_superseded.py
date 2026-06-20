"""Tests for stale helpers superseded by active main entities."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.yeelight_pro import entity_lifecycle
from custom_components.yeelight_pro.entity_lifecycle import (
    async_reconcile_entity_registry,
    entity_registry_reconcile_diagnostics,
)
from custom_components.yeelight_pro.identity import IDENTITY_SCOPE_KEY

from .entity_lifecycle_helpers import (
    FakeEntityRegistry,
    lifecycle_coordinator,
    patch_entity_registry,
    reconcile_diagnostics,
    registry_entry,
)
from .projection_helpers import projection_payload


@pytest.mark.asyncio
async def test_reconcile_disables_stale_helper_owned_by_active_main_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """已被主实体消费的旧 helper 残留应自动禁用，避免设备页继续显示错误控制."""
    scope = "private_endpoint_625450e28ea30c27_house_99529"
    stale_uid = f"yeelight_pro_{scope}_device_40266069_climate_1_acdfltr_number"
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id=stale_uid,
            entity_id=(
                "number.wen_kong_qi_1_wen_kong_qi_1_kong_diao_kong_zhi_"
                "air_conditioner_deflector_kong_diao_dao_feng_ban_xin_xi"
            ),
            domain="number",
            original_name="空调控制 air conditioner deflector,空调导风板信息",
        )
    ])
    coordinator = lifecycle_coordinator(data={40266069: _scoped_climate_payload(scope)})
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_unique_ids == {
        f"yeelight_pro_{scope}_device_40266069_climate_1_climate"
    }
    assert registry.updated_entities == [
        (
            "number.wen_kong_qi_1_wen_kong_qi_1_kong_diao_kong_zhi_"
            "air_conditioner_deflector_kong_diao_dao_feng_ban_xin_xi",
            {"disabled_by": entity_lifecycle.er.RegistryEntryDisabler.INTEGRATION},
        )
    ]
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == set()
    assert entity_registry_reconcile_diagnostics(coordinator) == reconcile_diagnostics(
        active=1,
        registry_entries=1,
        stale=1,
        pending_stale=0,
        disabled=1,
    )


@pytest.mark.asyncio
async def test_reconcile_preserves_user_named_stale_main_owned_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户自定义过名称的旧 helper 仍只进入 pending，不自动禁用."""
    scope = "private_endpoint_625450e28ea30c27_house_99529"
    stale_uid = f"yeelight_pro_{scope}_device_40266069_climate_1_acdfltr_number"
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id=stale_uid,
            entity_id="number.custom_deflector",
            domain="number",
            original_name="空调控制 air conditioner deflector,空调导风板信息",
            name="我的挡风板",
        )
    ])
    coordinator = lifecycle_coordinator(data={40266069: _scoped_climate_payload(scope)})
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert registry.updated_entities == []
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == {
        ("number", stale_uid)
    }


@pytest.mark.asyncio
async def test_reconcile_disables_stale_helper_replaced_by_new_helper_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同一属性从旧 helper 域迁移到新 helper 域时，应自动禁用旧实体."""
    scope = "private_endpoint_scope_house_1"
    stale_uid = f"yeelight_pro_{scope}_device_1001_other_mpml_switch"
    active_uid = f"yeelight_pro_{scope}_device_1001_other_mpml_number"
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id=stale_uid,
            entity_id="switch.p20_music_list",
            domain="switch",
            original_name="音乐播放器歌单ID",
        )
    ])
    coordinator = lifecycle_coordinator(data={1001: _music_number_payload(scope)})
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_uid in active_unique_ids
    assert registry.updated_entities == [
        (
            "switch.p20_music_list",
            {"disabled_by": entity_lifecycle.er.RegistryEntryDisabler.INTEGRATION},
        )
    ]
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == set()


@pytest.mark.asyncio
async def test_reconcile_disables_stale_component_event_replaced_by_main_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧的 switch_N_event 残留应在当前 switch_N 主实体存在时自动禁用."""
    scope = "private_endpoint_scope_house_1"
    stale_uid = f"yeelight_pro_{scope}_device_1002_switch_1_event"
    active_uid = f"yeelight_pro_{scope}_device_1002_switch_1"
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id=stale_uid,
            entity_id="event.scene_panel_key_1",
            domain="event",
            original_name="按键 1 事件",
        )
    ])
    coordinator = lifecycle_coordinator(data={1002: _switch_payload(scope)})
    patch_entity_registry(monkeypatch, registry)

    active_unique_ids = await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        coordinator,
    )

    assert active_uid in active_unique_ids
    assert registry.updated_entities == [
        (
            "event.scene_panel_key_1",
            {"disabled_by": entity_lifecycle.er.RegistryEntryDisabler.INTEGRATION},
        )
    ]
    assert getattr(coordinator, "_yeelight_pro_pending_stale_entity_keys") == set()


def _scoped_climate_payload(scope: str) -> dict:
    """Return a private-scope climate payload where acdfltr belongs to climate."""
    payload = projection_payload(
        device_id="40266069",
        category="temp_control",
        component_id="climate_1",
        component_category="air_conditioner",
        state={"acp": True, "actt": 26, "acct": 24, "acdfltr": 80},
        params={
            "1-acp": True,
            "1-actt": 26,
            "1-acct": 24,
            "1-acdfltr": 80,
        },
    )
    payload[IDENTITY_SCOPE_KEY] = scope
    payload["ha_device_instance"][IDENTITY_SCOPE_KEY] = scope
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "climate_1": {
                "acp": "1-acp",
                "actt": "1-actt",
                "acct": "1-acct",
                "acdfltr": "1-acdfltr",
            }
        }
    }
    payload["ha_product_model"]["components"][0]["properties"] = [
        {"prop_id": "acp", "access": "read_write", "property_type": "bool"},
        {
            "prop_id": "actt",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 16, "max": 32, "step": 1},
        },
        {"prop_id": "acct", "access": "read_only", "property_type": "int"},
        {
            "prop_id": "acdfltr",
            "name": "air conditioner deflector,空调导风板信息",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 0, "max": 255, "step": 1},
        },
    ]
    return payload


def _music_number_payload(scope: str) -> dict:
    """Return a music-component payload where mpml is now a number control."""
    payload = projection_payload(
        device_id="1001",
        category="other",
        component_id="other",
        component_category="other",
        state={},
        params={},
    )
    payload[IDENTITY_SCOPE_KEY] = scope
    payload["ha_device_instance"][IDENTITY_SCOPE_KEY] = scope
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mpml",
            "name": "音乐播放器歌单ID",
            "access": "read_write",
            "property_type": "int",
            "format": "uint16",
            "value_range": {"min": 0, "max": 65535, "step": 1},
        },
    ]
    return payload


def _switch_payload(scope: str) -> dict:
    """Return a switch payload whose old event helper is superseded."""
    payload = projection_payload(
        device_id="1002",
        category="relay_switch",
        component_id="switch_1",
        component_category="switch",
        state={"p": False},
        params={"1-p": False},
    )
    payload[IDENTITY_SCOPE_KEY] = scope
    payload["ha_device_instance"][IDENTITY_SCOPE_KEY] = scope
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "switch_1": {"p": "1-p"},
        }
    }
    payload["ha_product_model"]["components"][0]["properties"] = [
        {"prop_id": "p", "access": "read_write", "property_type": "bool"},
    ]
    return payload
