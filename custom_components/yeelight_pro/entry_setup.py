"""Config-entry setup helpers for Yeelight Pro."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    DOMAIN,
    get_enabled_platforms,
)
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import safe_error_summary
from .entity_lifecycle import async_reconcile_entity_registry
from .entry_migration import normalize_entry_data
from .ha_device_registry import async_sync_gateway_devices
from .lan_runtime import async_start_lan_runtime
from .repair_issues import async_create_topology_changed_issue
from .runtime_options import (
    async_options_updated,
    entry_options,
    topology_change_repairs_enabled,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_lan_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Yeelight Pro in LAN-only mode."""
    import asyncio

    from .lan_runtime import LanGatewayRuntime, lan_runtime_options

    entry_data = normalize_entry_data(entry.data)
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=None,
        house_id=0,
        options=entry_options(entry),
        entry_data=entry_data,
    )
    coordinator.data = {}
    await coordinator.async_config_entry_first_refresh()

    platforms = get_enabled_platforms(entry_options(entry))
    runtime_data: dict[str, Any] = {
        "client": None,
        "coordinator": coordinator,
        "entry": entry,
        "platforms": platforms,
    }
    hass.data[DOMAIN][entry.entry_id] = runtime_data

    lan_ip = str(entry_data.get(CONF_LAN_GATEWAY_IP, "")).strip()
    lan_port = int(entry_data.get(CONF_LAN_GATEWAY_PORT, 65443))
    if not lan_ip:
        _, host, port = lan_runtime_options(entry)
        lan_ip = host
        lan_port = port

    if lan_ip:
        try:
            # 创建拓扑就绪事件：第一个拓扑推送到达后才继续
            topology_ready = asyncio.Event()
            original_handler = coordinator.async_handle_lan_payload

            async def _lan_handler_with_topology_wait(
                payload: Mapping[str, Any],
            ) -> list:
                """拦截第一个拓扑推送，通知就绪事件."""
                result = await original_handler(payload)
                if not topology_ready.is_set():
                    from .lan_payload import lan_topology_update

                    if lan_topology_update(payload) is not None:
                        topology_ready.set()
                return result

            runtime = LanGatewayRuntime(host=lan_ip, port=lan_port)
            await runtime.async_start(_lan_handler_with_topology_wait)
            await runtime.async_get_topology()

            # 等待拓扑推送到达（最多 10 秒）
            try:
                await asyncio.wait_for(topology_ready.wait(), timeout=10.0)
                _LOGGER.info(
                    "Yeelight Pro LAN topology received for gateway %s:%s",
                    lan_ip,
                    lan_port,
                )
                # 网关在拓扑后立即发送属性同步（gateway_post.prop），
                # 短暂等待让属性更新到达，使平台能创建有状态的实体
                await asyncio.sleep(1)
            except asyncio.TimeoutError:
                _LOGGER.warning(
                    "Yeelight Pro LAN topology timeout for gateway %s:%s, "
                    "devices will appear after first topology push",
                    lan_ip,
                    lan_port,
                )

            runtime_data["lan_runtime"] = runtime
            coordinator.set_lan_runtime(runtime)
            _LOGGER.info("Yeelight Pro LAN runtime started: %s:%s", lan_ip, lan_port)
        except Exception as err:
            runtime_data["lan_runtime"] = OptionalRuntimeStartupFailure(err)
            coordinator.set_lan_runtime(None)
            _LOGGER.warning(
                "Yeelight Pro LAN runtime failed to start: %s",
                safe_error_summary(err),
            )
    else:
        _LOGGER.warning("Yeelight Pro LAN mode: no gateway IP configured")

    setup_topology_listener(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    await async_run_registry_maintenance(hass, entry, coordinator)
    _LOGGER.info(
        "Yeelight Pro LAN-only setup complete for gateway %s:%s",
        lan_ip,
        lan_port,
    )
    return True


async def async_run_registry_maintenance(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
) -> None:
    """Synchronize HA device/entity registry metadata for the loaded entry."""
    await async_sync_gateway_devices(hass, entry, coordinator)
    await async_reconcile_entity_registry(hass, entry, coordinator)


async def async_post_manual_refresh(
    entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
) -> None:
    """Run registry maintenance and topology repairs after a manual refresh."""
    hass = coordinator.hass
    previous_generation = coordinator.topology_generation
    await async_run_registry_maintenance(hass, entry, coordinator)
    if (
        coordinator.topology_generation != previous_generation
        and topology_change_repairs_enabled(entry)
    ):
        async_create_topology_changed_issue(
            hass,
            entry,
            coordinator,
            previous_generation=previous_generation,
        )


def setup_topology_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
) -> None:
    """Register topology-change maintenance for device and entity registries."""
    last_topology_generation = coordinator.topology_generation

    def _schedule_topology_sync() -> None:
        nonlocal last_topology_generation
        if coordinator.topology_generation == last_topology_generation:
            return
        previous_generation = last_topology_generation
        last_topology_generation = coordinator.topology_generation
        hass.async_create_task(async_sync_gateway_devices(hass, entry, coordinator))
        hass.async_create_task(async_reconcile_entity_registry(hass, entry, coordinator))
        if topology_change_repairs_enabled(entry):
            async_create_topology_changed_issue(
                hass,
                entry,
                coordinator,
                previous_generation=previous_generation,
            )

    entry.async_on_unload(coordinator.async_add_listener(_schedule_topology_sync))
    entry.async_on_unload(entry.add_update_listener(async_options_updated))


async def async_stop_loaded_runtime(data: Any) -> None:
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


async def async_start_optional_lan_runtime(
    entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
    runtime_data: dict[str, Any],
) -> None:
    """Start optional LAN runtime without blocking cloud polling fallback."""
    try:
        lan_runtime = await async_start_lan_runtime(entry, coordinator)
    except Exception as err:
        runtime_data["lan_runtime"] = OptionalRuntimeStartupFailure(err)
        coordinator.set_lan_runtime(None)
        _LOGGER.warning(
            "Yeelight Pro optional LAN runtime failed to start: %s",
            safe_error_summary(err),
        )
        return
    if lan_runtime is not None:
        runtime_data["lan_runtime"] = lan_runtime
        coordinator.set_lan_runtime(lan_runtime)
        _LOGGER.info(
            "Yeelight Pro LAN runtime started: %s:%s",
            lan_runtime.host,
            lan_runtime.port,
        )


class OptionalRuntimeStartupFailure:
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
