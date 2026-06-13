"""Yeelight Pro Integration for Home Assistant.

支持 Yeelight Pro 云端和私有部署两种模式。
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .area_service import async_register_area_services
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_CLOUD_DOMAIN,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
    DOMAIN,
    get_enabled_platforms,
)
from .core.client import YeelightProClient
from .core.analytics_coordinator import YeelightProAnalyticsCoordinator
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import AuthenticationError, ConnectionError, safe_error_summary
from .debug_service import async_register_debug_event_service
from .entry_setup import (
    async_post_manual_refresh as _async_post_manual_refresh,
    async_run_registry_maintenance as _async_run_registry_maintenance,
    async_setup_lan_entry as _async_setup_lan_entry,
    async_start_optional_lan_runtime as _async_start_optional_lan_runtime,
    async_stop_loaded_runtime as _async_stop_loaded_runtime,
    setup_topology_listener as _setup_topology_listener,
)
from .entry_migration import (
    async_migrate_config_entry,
    normalize_entry_data,
)
from .ha_device_registry import (
    active_device_identifiers as _active_device_identifiers,
    async_sync_gateway_devices as _async_sync_gateway_devices,
    device_payload_identifiers as _device_payload_identifiers,
)
from .live_runtime import async_start_live_runtime
from .oauth_refresh import async_refresh_entry_token
from .repair_issues import (
    async_delete_topology_changed_issues,
)
from .refresh_service import async_register_refresh_service
from .registry_cleanup_service import async_register_registry_cleanup_service
from .runtime_options import entry_options as _entry_options

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "_active_device_identifiers",
    "_async_sync_gateway_devices",
    "_device_payload_identifiers",
    "async_migrate_entry",
    "async_reload_entry",
    "async_remove_config_entry_device",
    "async_remove_entry",
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Yeelight Pro integration."""
    hass.data.setdefault(DOMAIN, {})

    async_register_area_services(hass)
    async_register_debug_event_service(hass)
    async_register_refresh_service(hass, _async_post_manual_refresh)
    async_register_registry_cleanup_service(hass)

    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a Yeelight Pro config entry."""
    return await async_migrate_config_entry(hass, entry)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yeelight Pro from a config entry."""
    entry_data = normalize_entry_data(entry.data)
    connection_mode = entry_data[CONF_CONNECTION_MODE]

    # LAN-only 模式：跳过云端客户端，纯局域网控制
    if connection_mode == CONNECTION_MODE_LAN:
        return await _async_setup_lan_entry(hass, entry)

    access_token = entry_data[CONF_ACCESS_TOKEN]
    client_id = entry_data.get(CONF_OPEN_API_CLIENT_ID, "")
    house_id = entry_data[CONF_HOUSE_ID]

    # 确定域名
    if connection_mode == CONNECTION_MODE_CLOUD:
        domain = entry_data[CONF_CLOUD_DOMAIN]
    else:
        domain = entry_data[CONF_PRIVATE_DOMAIN]

    # 创建客户端
    session = async_get_clientsession(hass)
    client = YeelightProClient(
        domain=domain,
        access_token=access_token,
        client_id=client_id,
        session=session,
    )
    client.set_token_refresh_handler(
        lambda: _async_refresh_runtime_token(hass, entry, client)
    )
    try:
        refresh_result = await async_refresh_entry_token(hass, entry, client)
        if refresh_result.refreshed:
            entry_data = refresh_result.entry_data
            access_token = entry_data[CONF_ACCESS_TOKEN]
            client_id = entry_data.get(CONF_OPEN_API_CLIENT_ID, "")
    except AuthenticationError:
        raise ConfigEntryAuthFailed("Yeelight Pro authentication failed") from None
    except ConnectionError as err:
        raise ConfigEntryNotReady(
            f"Connection failed: {safe_error_summary(err)}"
        ) from None

    # 验证服务可达性（仅检查连通性，token 在 config_flow 已验证）
    try:
        await client.check_health()
    except AuthenticationError:
        raise ConfigEntryAuthFailed("Yeelight Pro authentication failed") from None
    except ConnectionError as err:
        raise ConfigEntryNotReady(
            f"Connection failed: {safe_error_summary(err)}"
        ) from None

    # 创建协调器
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=client,
        house_id=house_id,
        options=_entry_options(entry),
        entry_data=entry_data,
    )

    # 首次数据更新
    await coordinator.async_config_entry_first_refresh()

    await _async_run_registry_maintenance(hass, entry, coordinator)

    analytics_coordinator = YeelightProAnalyticsCoordinator(
        hass,
        client,
        house_id,
        entry_data=coordinator.entry_data,
    )
    try:
        await analytics_coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning(
            "Yeelight Pro analytics setup degraded, exposing unavailable sensors: %s",
            safe_error_summary(err),
        )
    coordinator.analytics_enabled = True
    coordinator.analytics_data = analytics_coordinator.data
    analytics_coordinator.entry_data = dict(coordinator.entry_data)
    analytics_coordinator.houses = coordinator.houses
    analytics_coordinator._main_coordinator = coordinator
    analytics_coordinator._config_entry = entry

    # 存储到 hass.data
    platforms = get_enabled_platforms(_entry_options(entry))
    runtime_data = {
        "client": client,
        "coordinator": coordinator,
        "entry": entry,
        "platforms": platforms,
        "analytics_coordinator": analytics_coordinator,
    }
    hass.data[DOMAIN][entry.entry_id] = runtime_data

    try:
        push_manager = await async_start_live_runtime(hass, entry, coordinator)
        if push_manager is not None:
            runtime_data["push_manager"] = push_manager
    except Exception:
        await _async_stop_loaded_runtime(runtime_data)
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        raise
    await _async_start_optional_lan_runtime(entry, coordinator, runtime_data)

    # 拓扑变更监听
    _setup_topology_listener(hass, entry, coordinator)

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    await _async_run_registry_maintenance(hass, entry, coordinator)

    _LOGGER.info(
        "Yeelight Pro integration setup complete for house %s (%s mode)",
        house_id,
        connection_mode,
    )

    return True


async def _async_refresh_runtime_token(
    hass: HomeAssistant,
    entry: ConfigEntry,
    client: YeelightProClient,
) -> None:
    """Refresh an expired runtime token or preserve auth failure semantics."""
    try:
        await async_refresh_entry_token(hass, entry, client, force=True)
    except AuthenticationError:
        raise ConfigEntryAuthFailed("Yeelight Pro authentication failed") from None
    except ConnectionError as err:
        raise ConfigEntryNotReady(
            f"Connection failed: {safe_error_summary(err)}"
        ) from None


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    loaded = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    platforms = loaded.get("platforms", get_enabled_platforms(_entry_options(entry)))
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unload_ok:
        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        await _async_stop_loaded_runtime(data)
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove local artifacts for a config entry."""
    async_delete_topology_changed_issues(hass, entry)
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow local removal only for stale Yeelight Pro device entries."""
    yeelight_identifiers = {
        identifier for identifier in device_entry.identifiers if identifier[0] == DOMAIN
    }
    if not yeelight_identifiers:
        return False

    loaded = hass.data.get(DOMAIN, {}).get(config_entry.entry_id)
    coordinator = loaded.get("coordinator") if isinstance(loaded, Mapping) else None
    if not isinstance(coordinator, YeelightProCoordinator):
        return False

    active_identifiers = _active_device_identifiers(coordinator)
    if yeelight_identifiers & active_identifiers:
        _LOGGER.info(
            "Rejected local removal for active Yeelight Pro device %s",
            device_entry.id,
        )
        return False
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
