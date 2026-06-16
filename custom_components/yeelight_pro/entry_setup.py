"""Config-entry setup helpers for Yeelight Pro."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from inspect import isawaitable
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    CONF_LAN_GATEWAY_PRODUCT_ID,
    CONF_LOCAL_GATEWAY_PRODUCT_ID,
    DOMAIN,
    get_enabled_platforms,
)
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import safe_error_summary
from .entity_lifecycle import async_reconcile_entity_registry
from .entry_migration import normalize_entry_data
from .ha_device_registry import async_sync_gateway_devices
from .lan_runtime import async_start_lan_runtime
from .lan_runtime_endpoints import endpoint_kind_from_product_id
from .repair_issues import async_create_topology_changed_issue
from .runtime_options import (
    async_options_updated,
    entry_options,
    topology_change_repairs_enabled,
)

_LOGGER = logging.getLogger(__name__)
_LAN_TOPOLOGY_READY_TIMEOUT = 10.0
_LAN_INITIAL_STATE_READY_TIMEOUT = 1.0


@contextmanager
def config_entry_context(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> Iterator[None]:
    """在直接调用 setup 的测试路径中显式绑定当前 config entry。"""
    context_entry = hass.config_entries.async_get_entry(entry.entry_id) or entry
    token = config_entries.current_entry.set(context_entry)
    try:
        yield
    finally:
        config_entries.current_entry.reset(token)


async def async_setup_lan_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Yeelight Pro in LAN-only mode."""
    import asyncio

    from .lan_runtime import LanGatewayRuntime, lan_runtime_options

    entry_data = normalize_entry_data(entry.data)
    with config_entry_context(hass, entry):
        coordinator = YeelightProCoordinator(
            hass=hass,
            client=None,
            house_id=0,
            options=entry_options(entry),
            entry_data=entry_data,
        )
        await coordinator.async_config_entry_first_refresh()
    coordinator.data = {}
    coordinator.scenes = []
    coordinator.analytics_enabled = False
    coordinator.analytics_data = None

    platforms = get_enabled_platforms(entry_options(entry))
    runtime_data: dict[str, Any] = {
        "client": None,
        "coordinator": coordinator,
        "entry": entry,
        "entry_data": dict(entry_data),
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
            state_ready = asyncio.Event()
            original_handler = coordinator.async_handle_lan_payload

            async def _lan_handler_with_topology_wait(
                payload: Mapping[str, Any],
            ) -> list:
                """拦截首个拓扑/属性推送，通知启动就绪事件."""
                result = await original_handler(payload)
                from .lan_methods import METHOD_DEVICE_POST_PROP, METHOD_POST_PROP
                from .lan_payload import lan_topology_update

                if not topology_ready.is_set():
                    if lan_topology_update(payload) is not None:
                        topology_ready.set()
                if not state_ready.is_set() and payload.get("method") in {
                    METHOD_DEVICE_POST_PROP,
                    METHOD_POST_PROP,
                }:
                    state_ready.set()
                return result

            runtime = LanGatewayRuntime(
                host=lan_ip,
                port=lan_port,
                endpoint_kind=endpoint_kind_from_product_id(
                    entry_data.get(CONF_LAN_GATEWAY_PRODUCT_ID)
                    or entry_options(entry).get(CONF_LOCAL_GATEWAY_PRODUCT_ID)
                ),
            )
            await runtime.async_start(_lan_handler_with_topology_wait)
            await runtime.async_get_topology()

            # 等待拓扑推送到达（最多 10 秒）
            try:
                await asyncio.wait_for(
                    topology_ready.wait(),
                    timeout=_LAN_TOPOLOGY_READY_TIMEOUT,
                )
                _LOGGER.info(
                    "Yeelight Pro LAN topology received for gateway %s:%s",
                    lan_ip,
                    lan_port,
                )
                try:
                    await asyncio.wait_for(
                        state_ready.wait(),
                        timeout=_LAN_INITIAL_STATE_READY_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    _LOGGER.debug(
                        "Yeelight Pro LAN initial state sync not received before "
                        "platform setup for gateway %s:%s",
                        lan_ip,
                        lan_port,
                    )
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
            await async_cleanup_failed_setup(hass, entry, runtime_data)
            raise ConfigEntryNotReady(
                f"Yeelight Pro LAN gateway unavailable: {safe_error_summary(err)}"
            ) from err
    else:
        _LOGGER.warning("Yeelight Pro LAN mode: no gateway IP configured")

    try:
        setup_topology_listener(hass, entry, coordinator)
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
        await async_run_registry_maintenance(hass, entry, coordinator)
    except Exception:
        await async_cleanup_failed_setup(hass, entry, runtime_data)
        raise
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

    analytics_coordinator = data.get("analytics_coordinator")
    async_shutdown = getattr(analytics_coordinator, "async_shutdown", None)
    if callable(async_shutdown):
        await async_shutdown()

    client = data.get("client")
    disconnect = getattr(client, "disconnect", None)
    if callable(disconnect):
        await disconnect()


async def async_cleanup_failed_setup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    runtime_data: Mapping[str, Any],
) -> None:
    """Best-effort cleanup for setup failures after runtime objects are loaded."""
    try:
        await async_stop_loaded_runtime(runtime_data)
    except Exception as err:
        _LOGGER.warning(
            "Yeelight Pro setup cleanup failed: %s",
            safe_error_summary(err),
        )
    coordinator = runtime_data.get("coordinator")
    async_shutdown = getattr(coordinator, "async_shutdown", None)
    if callable(async_shutdown):
        try:
            result = async_shutdown()
            if isawaitable(result):
                await result
        except Exception as err:
            _LOGGER.warning(
                "Yeelight Pro coordinator shutdown after setup failure failed: %s",
                safe_error_summary(err),
            )
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)


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
