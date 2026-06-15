"""Config entry reload lifecycle tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN

from .config_entry_lifecycle_helpers import make_config_entry, register_config_entry


@pytest.mark.asyncio
async def test_reload_entry_stops_when_unload_fails(hass: HomeAssistant) -> None:
    """卸载失败时 reload 不能继续 setup，避免叠加 runtime。"""
    hass.data.setdefault(DOMAIN, {})
    entry = make_config_entry()
    register_config_entry(hass, entry)

    with patch(
        "custom_components.yeelight_pro.async_unload_entry",
        AsyncMock(return_value=False),
    ) as unload_entry, patch(
        "custom_components.yeelight_pro.async_setup_entry",
        AsyncMock(return_value=True),
    ) as setup_entry:
        from custom_components.yeelight_pro import async_reload_entry

        assert await async_reload_entry(hass, entry) is False

    unload_entry.assert_awaited_once_with(hass, entry)
    setup_entry.assert_not_awaited()


@pytest.mark.asyncio
async def test_reload_entry_sets_up_after_successful_unload(
    hass: HomeAssistant,
) -> None:
    """卸载成功时 reload 继续走 setup 并返回 setup 结果。"""
    hass.data.setdefault(DOMAIN, {})
    entry = make_config_entry()
    register_config_entry(hass, entry)

    with patch(
        "custom_components.yeelight_pro.async_unload_entry",
        AsyncMock(return_value=True),
    ) as unload_entry, patch(
        "custom_components.yeelight_pro.async_setup_entry",
        AsyncMock(return_value=True),
    ) as setup_entry:
        from custom_components.yeelight_pro import async_reload_entry

        assert await async_reload_entry(hass, entry) is True

    unload_entry.assert_awaited_once_with(hass, entry)
    setup_entry.assert_awaited_once_with(hass, entry)
