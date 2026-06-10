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

from .analytics_service import async_register_analytics_service
from .area_service import async_register_area_services
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_CLOUD_DOMAIN,
    CONF_HOUSE_ID,
    CONF_OAUTH_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_CLOUD,
    DOMAIN,
    get_enabled_platforms,
)
from .core.client import YeelightProClient
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import AuthenticationError, ConnectionError, safe_error_summary
from .debug_service import async_register_debug_event_service
from .entity_lifecycle import async_reconcile_entity_registry
from .entry_migration import (
    async_migrate_config_entry,
    normalize_entry_data,
)
from .ha_device_registry import (
    active_device_identifiers as _active_device_identifiers,
    async_sync_gateway_devices as _async_sync_gateway_devices,
    device_payload_identifiers as _device_payload_identifiers,
)
from .lan_runtime import async_start_lan_runtime
from .live_runtime import async_start_live_runtime
from .repair_issues import (
    async_create_topology_changed_issue,
    async_delete_topology_changed_issues,
)
from .refresh_service import async_register_refresh_service
from .registry_cleanup_service import async_register_registry_cleanup_service
from .runtime_options import (
    async_options_updated as _async_options_updated,
    entry_options as _entry_options,
    topology_change_repairs_enabled as _topology_change_repairs_enabled,
)

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
    async_register_analytics_service(hass)

    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a Yeelight Pro config entry."""
    return await async_migrate_config_entry(hass, entry)


async def _async_post_manual_refresh(
    entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
) -> None:
    """Run registry maintenance after a manual refresh."""
    hass = coordinator.hass
    previous_generation = coordinator.topology_generation
    await _async_sync_gateway_devices(hass, entry, coordinator)
    await async_reconcile_entity_registry(hass, entry, coordinator)
    if (
        coordinator.topology_generation != previous_generation
        and _topology_change_repairs_enabled(entry)
    ):
        async_create_topology_changed_issue(
            hass,
            entry,
            coordinator,
            previous_generation=previous_generation,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yeelight Pro from a config entry."""
    entry_data = normalize_entry_data(entry.data)
    connection_mode = entry_data[CONF_CONNECTION_MODE]
    access_token = entry_data[CONF_ACCESS_TOKEN]
    client_id = entry_data.get(CONF_OAUTH_CLIENT_ID, "")
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
    )

    # 首次数据更新
    await coordinator.async_config_entry_first_refresh()

    # 同步网关设备到 HA 注册表
    await _async_sync_gateway_devices(hass, entry, coordinator)

    # 记录过期实体注册表条目；显式 cleanup service 才会禁用 stale 实体。
    await async_reconcile_entity_registry(hass, entry, coordinator)

    # 存储到 hass.data
    platforms = get_enabled_platforms(_entry_options(entry))
    runtime_data = {
        "client": client,
        "coordinator": coordinator,
        "entry": entry,
        "platforms": platforms,
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

    # 拓扑变更监听：自动触发设备同步和实体 stale 记录
    last_topology_generation = coordinator.topology_generation

    def _schedule_topology_sync() -> None:
        nonlocal last_topology_generation
        if coordinator.topology_generation == last_topology_generation:
            return
        previous_generation = last_topology_generation
        last_topology_generation = coordinator.topology_generation
        hass.async_create_task(_async_sync_gateway_devices(hass, entry, coordinator))
        hass.async_create_task(async_reconcile_entity_registry(hass, entry, coordinator))
        if _topology_change_repairs_enabled(entry):
            async_create_topology_changed_issue(
                hass,
                entry,
                coordinator,
                previous_generation=previous_generation,
            )

    entry.async_on_unload(coordinator.async_add_listener(_schedule_topology_sync))
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    _LOGGER.info(
        "Yeelight Pro integration setup complete for house %s (%s mode)",
        house_id,
        connection_mode,
    )

    return True


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


async def _async_stop_loaded_runtime(data: Any) -> None:
    """Stop optional runtime managers and disconnect the client."""
    if not isinstance(data, Mapping):
        return

    push_manager = data.get("push_manager")
    stop_push = getattr(push_manager, "async_stop", None)
    if callable(stop_push):
        await stop_push()

    lan_runtime = data.get("lan_runtime")
    stop_lan = getattr(lan_runtime, "async_stop", None)
    if callable(stop_lan):
        await stop_lan()

    client = data.get("client")
    disconnect = getattr(client, "disconnect", None)
    if callable(disconnect):
        await disconnect()


async def _async_start_optional_lan_runtime(
    entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
    runtime_data: dict[str, Any],
) -> None:
    """Start optional LAN runtime without blocking cloud polling fallback."""
    try:
        lan_runtime = await async_start_lan_runtime(entry, coordinator)
    except Exception as err:
        runtime_data["lan_runtime"] = _OptionalRuntimeStartupFailure(err)
        coordinator.set_lan_runtime(None)
        _LOGGER.warning(
            "Yeelight Pro optional LAN runtime failed to start: %s",
            safe_error_summary(err),
        )
        return
    if lan_runtime is not None:
        runtime_data["lan_runtime"] = lan_runtime
        coordinator.set_lan_runtime(lan_runtime)


class _OptionalRuntimeStartupFailure:
    """Diagnostics-safe health object for a failed optional runtime startup."""

    def __init__(self, err: BaseException) -> None:
        """Store only the exception type, not the message or endpoint."""
        self.health = _OptionalRuntimeStartupFailureHealth(type(err).__name__)


class _OptionalRuntimeStartupFailureHealth:
    """Expose aggregate runtime failure health through diagnostics."""

    def __init__(self, error_type: str) -> None:
        """Initialize aggregate-only failure health."""
        self._error_type = error_type

    def as_dict(self) -> dict[str, Any]:
        """Return a diagnostics-safe LAN health shape."""
        return {
            "running": False,
            "connected": False,
            "sent_count": 0,
            "received_count": 0,
            "last_error_type": self._error_type,
        }


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
