"""Registry cleanup service tests."""

from __future__ import annotations

import pytest

from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import entity_registry as er

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.registry_cleanup_service import (
    ATTR_AUDIT_ID,
    ATTR_CONFIRM,
    ATTR_ENTRY_ID,
    ERROR_ADMIN_CONTEXT_REQUIRED,
    ERROR_AUDIT_MISMATCH,
    ERROR_CONFIRM_REQUIRES_AUDIT,
    async_register_registry_cleanup_service,
)

from .entity_lifecycle_helpers import (
    FakeEntityRegistry,
    patch_entity_registry,
    registry_entry,
)
from .registry_cleanup_service_helpers import (
    admin_context,
    call_cleanup_registry,
    install_cleanup_runtime,
    patch_device_registry,
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
    coordinator = install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    patch_device_registry(monkeypatch, stale_device_count=1)

    async_register_registry_cleanup_service(hass)
    response = await call_cleanup_registry(hass, context=await admin_context(hass))

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
    coordinator = install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    context = await admin_context(hass)
    dry_run = await call_cleanup_registry(
        hass,
        {ATTR_ENTRY_ID: "entry-1"},
        context=context,
    )
    response = await call_cleanup_registry(
        hass,
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_CONFIRM: True,
            ATTR_AUDIT_ID: dry_run["entries"][0]["audit_id"],
        },
        context=context,
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
async def test_cleanup_registry_service_disables_entities_excluded_by_import_filter(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """picker/filter 排除的既有设备实体只能经显式 cleanup confirm 禁用."""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_blocked-light_light",
            entity_id="light.blocked",
            domain="light",
        )
    ])
    install_cleanup_runtime(
        hass,
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
    patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    context = await admin_context(hass)
    dry_run = await call_cleanup_registry(
        hass,
        {ATTR_ENTRY_ID: "entry-1"},
        context=context,
    )
    response = await call_cleanup_registry(
        hass,
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_CONFIRM: True,
            ATTR_AUDIT_ID: dry_run["entries"][0]["audit_id"],
        },
        context=context,
    )

    assert dry_run["entries"][0]["stale_entities"] == 1
    assert dry_run["entries"][0]["entity_domains"] == {"light": 1}
    assert response["disabled_entities"] == 1
    assert registry.updated_entities == [
        ("light.blocked", er.RegistryEntryDisabler.INTEGRATION)
    ]
    assert registry.removed_entity_ids == []


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
    coordinator = install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    with pytest.raises(ServiceValidationError, match=ERROR_AUDIT_MISMATCH):
        await call_cleanup_registry(
            hass,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_CONFIRM: True,
                ATTR_AUDIT_ID: "wrong-audit-id",
            },
            context=await admin_context(hass),
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
    install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, FakeEntityRegistry([]))
    patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    with pytest.raises(ServiceValidationError, match=ERROR_CONFIRM_REQUIRES_AUDIT):
        await call_cleanup_registry(
            hass,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_CONFIRM: True,
            },
            context=await admin_context(hass),
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
    install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    context = await admin_context(hass)
    dry_run = await call_cleanup_registry(
        hass,
        {ATTR_ENTRY_ID: "entry-1"},
        context=context,
    )
    coordinator = hass.data[DOMAIN]["entry-1"]["coordinator"]
    delattr(coordinator, "_yeelight_pro_last_entity_registry_cleanup_audit")

    with pytest.raises(ServiceValidationError, match=ERROR_AUDIT_MISMATCH):
        await call_cleanup_registry(
            hass,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_CONFIRM: True,
                ATTR_AUDIT_ID: dry_run["entries"][0]["audit_id"],
            },
            context=context,
        )

    assert registry.updated_entities == []
    assert registry.removed_entity_ids == []


@pytest.mark.asyncio
async def test_cleanup_registry_service_preserves_user_disabled_stale_entity(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户禁用的 stale entry 不进入 cleanup dry-run，也不会被 confirm 改写。"""
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id="yeelight_pro_scene_user_disabled",
            entity_id="scene.user_disabled",
            domain="scene",
            disabled_by=er.RegistryEntryDisabler.USER,
        )
    ])
    install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    context = await admin_context(hass)
    dry_run = await call_cleanup_registry(
        hass,
        {ATTR_ENTRY_ID: "entry-1"},
        context=context,
    )
    response = await call_cleanup_registry(
        hass,
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_CONFIRM: True,
            ATTR_AUDIT_ID: dry_run["entries"][0]["audit_id"],
        },
        context=context,
    )

    assert dry_run["entries"][0]["stale_entities"] == 0
    assert dry_run["entries"][0]["entity_domains"] == {}
    assert response["disabled_entities"] == 0
    assert response["skipped_entities"] == 0
    assert registry.updated_entities == []
    assert registry.removed_entity_ids == []
    assert registry.entries[0].disabled_by == er.RegistryEntryDisabler.USER


@pytest.mark.asyncio
async def test_cleanup_registry_service_rejects_non_admin_user(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """cleanup registry 会修改 HA registry，必须限制为管理员调用."""
    install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, FakeEntityRegistry([]))
    patch_device_registry(monkeypatch, stale_device_count=0)
    user = await hass.auth.async_create_system_user(
        "limited",
        group_ids=[GROUP_ID_USER],
    )

    async_register_registry_cleanup_service(hass)
    with pytest.raises(Unauthorized):
        await call_cleanup_registry(
            hass,
            context=Context(user_id=user.id),
        )


@pytest.mark.asyncio
async def test_cleanup_registry_service_rejects_missing_user_context(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """registry cleanup 必须来自明确的管理员用户上下文。"""
    coordinator = install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, FakeEntityRegistry([]))
    patch_device_registry(monkeypatch, stale_device_count=0)

    async_register_registry_cleanup_service(hass)
    with pytest.raises(Unauthorized) as exc_info:
        await call_cleanup_registry(hass)

    assert str(exc_info.value) == "Unauthorized"
    assert exc_info.value.permission == ERROR_ADMIN_CONTEXT_REQUIRED
    assert not hasattr(
        coordinator,
        "_yeelight_pro_last_entity_registry_cleanup_audit",
    )
