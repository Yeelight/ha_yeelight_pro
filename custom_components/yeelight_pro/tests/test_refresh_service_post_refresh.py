"""Post manual-refresh maintenance tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import CONF_TOPOLOGY_CHANGE_REPAIRS

from .refresh_service_helpers import refresh_coordinator, refresh_entry


@pytest.mark.asyncio
async def test_post_manual_refresh_runs_registry_maintenance(
    hass: HomeAssistant,
) -> None:
    """Post-refresh hook should sync devices and reconcile entity registry."""
    from custom_components.yeelight_pro import _async_post_manual_refresh

    entry = refresh_entry("entry-1")
    coordinator = refresh_coordinator(hass)

    with pytest.MonkeyPatch.context() as monkeypatch:
        sync_devices = AsyncMock()
        reconcile = AsyncMock()
        monkeypatch.setattr(
            "custom_components.yeelight_pro._async_sync_gateway_devices",
            sync_devices,
        )
        monkeypatch.setattr(
            "custom_components.yeelight_pro.async_reconcile_entity_registry",
            reconcile,
        )

        await _async_post_manual_refresh(entry, coordinator)

    sync_devices.assert_awaited_once_with(hass, entry, coordinator)
    reconcile.assert_awaited_once_with(hass, entry, coordinator)


@pytest.mark.asyncio
async def test_post_manual_refresh_creates_repair_issue_on_topology_change(
    hass: HomeAssistant,
) -> None:
    """手动刷新后如果拓扑变化，默认创建 Repairs 提示。"""
    from custom_components.yeelight_pro import _async_post_manual_refresh

    entry = refresh_entry("entry-1")
    entry.options = {}
    coordinator = refresh_coordinator(hass)

    async def _sync_devices(*_args):
        coordinator.topology_generation = 2

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "custom_components.yeelight_pro._async_sync_gateway_devices",
            AsyncMock(side_effect=_sync_devices),
        )
        monkeypatch.setattr(
            "custom_components.yeelight_pro.async_reconcile_entity_registry",
            AsyncMock(),
        )
        create_issue = MagicMock()
        monkeypatch.setattr(
            "custom_components.yeelight_pro.async_create_topology_changed_issue",
            create_issue,
        )

        await _async_post_manual_refresh(entry, coordinator)

    create_issue.assert_called_once_with(
        hass,
        entry,
        coordinator,
        previous_generation=1,
    )


@pytest.mark.asyncio
async def test_post_manual_refresh_respects_disabled_topology_repairs_option(
    hass: HomeAssistant,
) -> None:
    """手动刷新后拓扑变化也必须尊重 Repairs 提示开关。"""
    from custom_components.yeelight_pro import _async_post_manual_refresh

    entry = refresh_entry("entry-1")
    entry.options = {CONF_TOPOLOGY_CHANGE_REPAIRS: False}
    coordinator = refresh_coordinator(hass)

    async def _sync_devices(*_args):
        coordinator.topology_generation = 2

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "custom_components.yeelight_pro._async_sync_gateway_devices",
            AsyncMock(side_effect=_sync_devices),
        )
        monkeypatch.setattr(
            "custom_components.yeelight_pro.async_reconcile_entity_registry",
            AsyncMock(),
        )
        create_issue = MagicMock()
        monkeypatch.setattr(
            "custom_components.yeelight_pro.async_create_topology_changed_issue",
            create_issue,
        )

        await _async_post_manual_refresh(entry, coordinator)

    create_issue.assert_not_called()
