"""Config entry unload and removal lifecycle tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN

from .config_entry_lifecycle_helpers import make_config_entry, make_coordinator


@pytest.mark.asyncio
async def test_unload_entry(hass: HomeAssistant) -> None:
    """Unload should remove runtime, stop push manager, and disconnect client."""
    config_entry = make_config_entry()
    coordinator = make_coordinator(hass, AsyncMock())
    client_mock = AsyncMock()
    client_mock.disconnect = AsyncMock()
    push_manager = AsyncMock()
    lan_runtime = AsyncMock()
    hass.data[DOMAIN] = {
        config_entry.entry_id: {
            "client": client_mock,
            "coordinator": coordinator,
            "push_manager": push_manager,
            "lan_runtime": lan_runtime,
        }
    }

    from custom_components.yeelight_pro import async_unload_entry

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(hass, config_entry)

    assert result is True
    push_manager.async_stop.assert_awaited_once()
    lan_runtime.async_stop.assert_awaited_once()
    client_mock.disconnect.assert_awaited_once()
    assert config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_entry_is_idempotent_without_loaded_runtime(
    hass: HomeAssistant,
) -> None:
    """Unload should be idempotent if runtime data is already absent."""
    config_entry = make_config_entry()
    hass.data[DOMAIN] = {}

    from custom_components.yeelight_pro import async_unload_entry

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(hass, config_entry)

    assert result is True


@pytest.mark.asyncio
async def test_unload_entry_keeps_runtime_when_platform_unload_fails(
    hass: HomeAssistant,
) -> None:
    """Failed platform unload should keep runtime and client connection."""
    config_entry = make_config_entry()
    coordinator = make_coordinator(hass, AsyncMock())
    client_mock = AsyncMock()
    client_mock.disconnect = AsyncMock()
    push_manager = AsyncMock()
    hass.data[DOMAIN] = {
        config_entry.entry_id: {
            "client": client_mock,
            "coordinator": coordinator,
            "push_manager": push_manager,
        }
    }

    from custom_components.yeelight_pro import async_unload_entry

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=False,
    ):
        result = await async_unload_entry(hass, config_entry)

    assert result is False
    assert config_entry.entry_id in hass.data[DOMAIN]
    push_manager.async_stop.assert_not_awaited()
    client_mock.disconnect.assert_not_awaited()


@pytest.mark.asyncio
async def test_unload_entry_keeps_runtime_when_push_stop_fails(
    hass: HomeAssistant,
) -> None:
    """Push manager stop 失败时保留 runtime，允许下一次 unload 重试."""
    config_entry = make_config_entry()
    coordinator = make_coordinator(hass, AsyncMock())
    client_mock = AsyncMock()
    client_mock.disconnect = AsyncMock()
    push_manager = AsyncMock()
    push_manager.async_stop.side_effect = OSError("token-secret")
    hass.data[DOMAIN] = {
        config_entry.entry_id: {
            "client": client_mock,
            "coordinator": coordinator,
            "push_manager": push_manager,
        }
    }

    from custom_components.yeelight_pro import async_unload_entry

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        with pytest.raises(OSError):
            await async_unload_entry(hass, config_entry)

    assert config_entry.entry_id in hass.data[DOMAIN]
    push_manager.async_stop.assert_awaited_once()
    client_mock.disconnect.assert_not_awaited()


@pytest.mark.asyncio
async def test_unload_entry_keeps_runtime_when_client_disconnect_fails(
    hass: HomeAssistant,
) -> None:
    """Client disconnect 失败时保留 runtime，避免丢失后续清理入口."""
    config_entry = make_config_entry()
    coordinator = make_coordinator(hass, AsyncMock())
    client_mock = AsyncMock()
    client_mock.disconnect = AsyncMock(side_effect=OSError("token-secret"))
    push_manager = AsyncMock()
    hass.data[DOMAIN] = {
        config_entry.entry_id: {
            "client": client_mock,
            "coordinator": coordinator,
            "push_manager": push_manager,
        }
    }

    from custom_components.yeelight_pro import async_unload_entry

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        with pytest.raises(OSError):
            await async_unload_entry(hass, config_entry)

    assert config_entry.entry_id in hass.data[DOMAIN]
    push_manager.async_stop.assert_awaited_once()
    client_mock.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_entry_cleans_local_topology_repair_issues(
    hass: HomeAssistant,
) -> None:
    """Removing a config entry should clear local Repairs artifacts only."""
    config_entry = make_config_entry()

    from custom_components.yeelight_pro import async_remove_entry

    with patch(
        "custom_components.yeelight_pro.async_delete_topology_changed_issues",
    ) as delete_issues:
        result = await async_remove_entry(hass, config_entry)

    assert result is True
    delete_issues.assert_called_once_with(hass, config_entry)
