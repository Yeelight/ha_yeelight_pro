"""Yeelight Pro Integration for Home Assistant.

支持 Yeelight Pro 云端和私有部署两种模式。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_CLOUD_DOMAIN,
    CONF_PRIVATE_DOMAIN,
    CONF_HOUSE_ID,
    CONNECTION_MODE_CLOUD,
    DOMAIN,
    PLATFORMS,
)
from .core.client import YeelightProClient
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import AuthenticationError, ConnectionError

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Yeelight Pro integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yeelight Pro from a config entry."""
    # 获取配置
    connection_mode = entry.data[CONF_CONNECTION_MODE]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    house_id = entry.data[CONF_HOUSE_ID]

    # 确定域名
    if connection_mode == CONNECTION_MODE_CLOUD:
        domain = entry.data.get(CONF_CLOUD_DOMAIN, "api.yeelight.com")
    else:
        domain = entry.data.get(CONF_PRIVATE_DOMAIN, "192.168.1.100:8080")

    # 创建客户端
    session = async_get_clientsession(hass)
    client = YeelightProClient(
        domain=domain,
        access_token=access_token,
        session=session,
    )

    # 验证连接
    try:
        await client.validate_connection()
    except AuthenticationError as err:
        _LOGGER.error("Authentication failed: %s", err)
        return False
    except ConnectionError as err:
        raise ConfigEntryNotReady(f"Connection failed: {err}") from err

    # 创建协调器
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=client,
        house_id=house_id,
    )

    # 首次数据更新
    await coordinator.async_config_entry_first_refresh()

    # 存储到 hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "Yeelight Pro integration setup complete for house %s (%s mode)",
        house_id,
        connection_mode,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["client"].disconnect()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
