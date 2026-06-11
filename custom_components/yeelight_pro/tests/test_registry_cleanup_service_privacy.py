"""Registry cleanup privacy and replay-safety tests."""

from __future__ import annotations

import logging

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.yeelight_pro.registry_cleanup_service import (
    ATTR_AUDIT_ID,
    ATTR_CONFIRM,
    ATTR_ENTRY_ID,
    ERROR_AUDIT_MISMATCH,
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
async def test_cleanup_registry_service_response_and_logs_are_identifier_safe(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """cleanup B 只返回聚合结果，不能泄露 stale registry 或设备标识。"""
    secret_unique_id = "yeelight_pro_scene_secret_unique"
    secret_entity_id = "scene.secret_stale"
    secret_device_id = "secret-device-identifier"
    registry = FakeEntityRegistry([
        registry_entry(
            unique_id=secret_unique_id,
            entity_id=secret_entity_id,
            domain="scene",
        )
    ])
    install_cleanup_runtime(hass)
    patch_entity_registry(monkeypatch, registry)
    patch_device_registry(
        monkeypatch,
        stale_device_count=1,
        identifiers=[secret_device_id],
    )

    async_register_registry_cleanup_service(hass)
    context = await admin_context(hass)
    dry_run = await call_cleanup_registry(
        hass,
        {ATTR_ENTRY_ID: "entry-1"},
        context=context,
    )
    caplog.set_level(
        logging.INFO,
        logger="custom_components.yeelight_pro.registry_cleanup_service",
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

    integration_logs = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "custom_components.yeelight_pro.registry_cleanup_service"
    )
    visible_payload = f"{dry_run} {response} {integration_logs}"
    assert secret_unique_id not in visible_payload
    assert secret_entity_id not in visible_payload
    assert secret_device_id not in visible_payload
    assert "entry-1" not in integration_logs
    assert "disabled=1" in integration_logs
    assert registry.updated_entities == [
        (secret_entity_id, {"disabled_by": er.RegistryEntryDisabler.INTEGRATION})
    ]
    assert registry.removed_entity_ids == []


@pytest.mark.asyncio
async def test_cleanup_registry_service_rejects_stale_audit_after_topology_change(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """dry-run 后 stale 集合变化时，旧 audit_id 不能被重放确认。"""
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
    registry.entries.append(
        registry_entry(
            unique_id="yeelight_pro_switch_new_stale",
            entity_id="switch.new_stale",
            domain="switch",
        )
    )

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
    audit = getattr(coordinator, "_yeelight_pro_last_entity_registry_cleanup_audit")
    assert audit.status == "rejected"
    assert audit.stale_entities == 2
    assert audit.entity_domains == {"scene": 1, "switch": 1}
