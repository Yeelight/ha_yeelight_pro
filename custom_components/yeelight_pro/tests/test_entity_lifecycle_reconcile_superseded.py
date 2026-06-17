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
