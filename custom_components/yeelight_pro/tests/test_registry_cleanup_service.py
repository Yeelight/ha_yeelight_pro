"""Registry cleanup service tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import entity_registry as er

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.registry_cleanup_service import (
    ATTR_AUDIT_ID,
    ATTR_CONFIRM,
    ATTR_ENTRY_ID,
    ERROR_AUDIT_MISMATCH,
    ERROR_CONFIRM_REQUIRES_AUDIT,
    SERVICE_CLEANUP_REGISTRY,
    async_register_registry_cleanup_service,
)

from .entity_lifecycle_helpers import (
    FakeEntityRegistry,
    lifecycle_coordinator,
    patch_entity_registry,
    registry_entry,
)


@pytest.mark.asyncio
async def test_cleanup_registry_service_dry_run_returns_audit_id(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dry-run 返回聚合 audit id，不禁用、不删除 registry entry."""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_scene_stale",
            entity_id="scene.stale",
            domain="scene",
        )
    ])
    coordinator = _install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    _patch_device_registry(monkeypatch, stale_device_count=1)

    async_register_registry_cleanup_service(hass)
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEANUP_REGISTRY,
        blocking=True,
        return_response=True,
    )

    assert response["action"] == "dry_run"
    assert response["total_stale_entities"] == 1
    assert response["total_stale_devices"] == 1
    assert response["entries"][0]["entry_id"] == "entry-1"
    assert response["entries"][0]["stale_entities"] == 1
    assert response["entries"][0]["entity_domains"] == {"scene": 1}
    assert response["entries"][0]["audit_id"]
    assert registry.updated_entities == []
    assert registry.removed_entity_ids == []
    assert getattr(coordinator, "_yeelight_pro_last_entity_registry_cleanup_audit").status == "dry_run"


@pytest.mark.asyncio
async def test_cleanup_registry_service_confirm_disables_stale_entities(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """confirm 必须匹配 dry-run audit id，并且只 disable stale entities."""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_scene_stale",
            entity_id="scene.stale",
            domain="scene",
        )
    ])
    coordinator = _install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    _patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    dry_run = await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEANUP_REGISTRY,
        {ATTR_ENTRY_ID: "entry-1"},
        blocking=True,
        return_response=True,
    )
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEANUP_REGISTRY,
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_CONFIRM: True,
            ATTR_AUDIT_ID: dry_run["entries"][0]["audit_id"],
        },
        blocking=True,
        return_response=True,
    )

    assert response["action"] == "confirm"
    assert response["status"] == "confirmed"
    assert response["disabled_entities"] == 1
    assert response["stale_devices"] == 0
    assert registry.updated_entities == [
        ("scene.stale", er.RegistryEntryDisabler.INTEGRATION)
    ]
    assert registry.removed_entity_ids == []
    audit = getattr(coordinator, "_yeelight_pro_last_entity_registry_cleanup_audit")
    assert audit.status == "confirmed"
    assert audit.disabled_entities == 1


@pytest.mark.asyncio
async def test_cleanup_registry_service_rejects_mismatched_audit_id(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stale 结果和 audit_id 不匹配时必须拒绝执行."""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_scene_stale",
            entity_id="scene.stale",
            domain="scene",
        )
    ])
    coordinator = _install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    _patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    with pytest.raises(ServiceValidationError, match=ERROR_AUDIT_MISMATCH):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLEANUP_REGISTRY,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_CONFIRM: True,
                ATTR_AUDIT_ID: "wrong-audit-id",
            },
            blocking=True,
            return_response=True,
        )

    assert registry.updated_entities == []
    assert registry.removed_entity_ids == []
    assert getattr(coordinator, "_yeelight_pro_last_entity_registry_cleanup_audit").status == "rejected"


@pytest.mark.asyncio
async def test_cleanup_registry_service_confirm_requires_audit_id(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """confirm 没有 audit_id 时必须拒绝，避免跳过 dry-run."""
    _install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, FakeEntityRegistry([]))
    _patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    with pytest.raises(ServiceValidationError, match=ERROR_CONFIRM_REQUIRES_AUDIT):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLEANUP_REGISTRY,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_CONFIRM: True,
            },
            blocking=True,
            return_response=True,
        )


@pytest.mark.asyncio
async def test_cleanup_registry_service_confirm_requires_prior_dry_run(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """即使 audit_id 形状正确，未先 dry-run 也不能执行 confirm."""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_scene_stale",
            entity_id="scene.stale",
            domain="scene",
        )
    ])
    _install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    _patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    dry_run = await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEANUP_REGISTRY,
        {ATTR_ENTRY_ID: "entry-1"},
        blocking=True,
        return_response=True,
    )
    coordinator = hass.data[DOMAIN]["entry-1"]["coordinator"]
    delattr(coordinator, "_yeelight_pro_last_entity_registry_cleanup_audit")

    with pytest.raises(ServiceValidationError, match=ERROR_AUDIT_MISMATCH):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLEANUP_REGISTRY,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_CONFIRM: True,
                ATTR_AUDIT_ID: dry_run["entries"][0]["audit_id"],
            },
            blocking=True,
            return_response=True,
        )

    assert registry.updated_entities == []
    assert registry.removed_entity_ids == []


@pytest.mark.asyncio
async def test_cleanup_registry_service_rejects_non_admin_user(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """cleanup registry 会修改 HA registry，必须限制为管理员调用."""
    _install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, FakeEntityRegistry([]))
    _patch_device_registry(monkeypatch, stale_device_count=0)
    user = await hass.auth.async_create_system_user(
        "limited",
        group_ids=[GROUP_ID_USER],
    )

    async_register_registry_cleanup_service(hass)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLEANUP_REGISTRY,
            blocking=True,
            context=Context(user_id=user.id),
            return_response=True,
        )


def _install_cleanup_runtime(hass: HomeAssistant) -> SimpleNamespace:
    """Install a focused runtime entry for cleanup service tests."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-1"
    coordinator = lifecycle_coordinator()
    coordinator.hass = hass
    coordinator.get_gateway_devices = lambda: {}
    hass.data[DOMAIN] = {
        "entry-1": {
            "entry": entry,
            "coordinator": coordinator,
        }
    }
    return coordinator


def _patch_device_registry(
    monkeypatch: pytest.MonkeyPatch,
    *,
    stale_device_count: int,
) -> None:
    """Patch HA device registry helpers with aggregate stale device fixtures."""
    entries = [
        SimpleNamespace(
            id=f"device-{index}",
            identifiers={(DOMAIN, f"stale-device-{index}")},
        )
        for index in range(stale_device_count)
    ]
    fake_registry = SimpleNamespace(entries=entries)
    monkeypatch.setattr(
        "custom_components.yeelight_pro.entity_lifecycle_cleanup.dr.async_get",
        lambda hass: fake_registry,
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.entity_lifecycle_cleanup.dr.async_entries_for_config_entry",
        lambda device_registry, entry_id: device_registry.entries,
    )
