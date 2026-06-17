"""Yeelight Pro 数据协调器."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Mapping

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import (
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_SCAN_INTERVAL,
    DEFAULT_DEBUG_MODE,
    DEFAULT_HIDE_UNKNOWN_ENTITIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from ..identity import apply_identity_scope_to_device_maps
from .auxiliary_data import AuxiliaryData, async_fetch_auxiliary_data
from .client import YeelightProClient
from .coordinator_controls import CoordinatorControlMixin
from .device_payload import DevicePayloadBuilder
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    safe_error_summary,
)
from .property_hydration import async_hydrate_device_properties
from .property_hydration_summary import PropertyHydrationDiagnostics
from .coordinator_runtime import CoordinatorRuntimeMixin
from .runtime_bridge import RuntimeEventDeduper, RuntimePropertyUpdateSummary
from .runtime_state import RuntimeStateStore
from .schema_cache import ProductSchemaCache, product_ids_from_items
from .topology_diff import TopologyDiffSummary
from .topology_tracker import TopologyTracker

_LOGGER = logging.getLogger(__name__)


class YeelightProCoordinator(
    CoordinatorRuntimeMixin,
    CoordinatorControlMixin,
    DataUpdateCoordinator,
):
    """Yeelight Pro 数据协调器."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: YeelightProClient | None = None,
        house_id: int = 0,
        options: Mapping[str, Any] | None = None,
        entry_data: Mapping[str, Any] | None = None,
    ):
        """初始化协调器."""
        self.options = dict(options or {})
        self.entry_data = dict(entry_data or {})
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=self.scan_interval),
        )
        self.client = client
        self.house_id = house_id
        self.devices: Dict[int, Dict[str, Any]] = {}
        self.gateways: Dict[int, Dict[str, Any]] = {}
        self.areas: list[dict[str, Any]] = []
        self.rooms: list[dict[str, Any]] = []
        self.groups: list[dict[str, Any]] = []
        self.houses: list[dict[str, Any]] = []
        self.scenes: list[dict[str, Any]] = []
        self.analytics_enabled = False
        self.analytics_data: Any | None = None
        self._runtime_state = RuntimeStateStore()
        self._push_event_deduper = RuntimeEventDeduper()
        self.last_push_property_summary = RuntimePropertyUpdateSummary()
        self.last_push_event_count = 0
        self._topology_tracker = TopologyTracker()
        self._device_payload_builder = DevicePayloadBuilder()
        self._product_schema_cache = ProductSchemaCache(hass)
        self.property_hydration_diagnostics: dict[str, int] = {}
        self._force_product_schema_refresh = False
        self._lan_runtime: Any | None = None

    @property
    def scan_interval(self) -> int:
        """返回当前轮询间隔配置."""
        return int(self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    def apply_options(self, options: Mapping[str, Any]) -> None:
        """Apply runtime-safe options without reloading the config entry."""
        self.options = dict(options)
        self.update_interval = timedelta(seconds=self.scan_interval)

    @property
    def debug_mode(self) -> bool:
        """返回是否启用调试能力."""
        return bool(self.options.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE))

    @property
    def hide_unknown_entities(self) -> bool:
        """返回是否隐藏未知能力生成的通用实体."""
        return bool(
            self.options.get(
                CONF_HIDE_UNKNOWN_ENTITIES,
                DEFAULT_HIDE_UNKNOWN_ENTITIES,
            )
        )

    def set_lan_runtime(self, lan_runtime: Any | None) -> None:
        """Attach the optional local gateway runtime used for device writes."""
        self._lan_runtime = lan_runtime

    async def _async_update_data(self) -> Dict[int, Any]:
        """从 API 获取数据（LAN-only 模式下跳过云端轮询）."""
        if self.client is None:
            # LAN-only 模式：数据由 LAN 拓扑推送驱动，不做云端轮询
            return self.devices
        client = self.client

        try:
            devices = await client.get_devices(self.house_id)

            gateways = await self._async_get_gateways(client)

            product_schemas = await self._async_get_product_schemas(
                client,
                [*devices, *gateways]
            )
            hydration_diagnostics = PropertyHydrationDiagnostics()
            devices = await async_hydrate_device_properties(
                client,
                house_id=self.house_id,
                devices=devices,
                product_schemas=product_schemas,
                diagnostics=hydration_diagnostics,
            )
            self.property_hydration_diagnostics = hydration_diagnostics.as_dict()

            await self._async_fetch_auxiliary_data()

            data, gateway_data = self._device_payload_builder.build_runtime_payloads(
                devices=devices,
                gateways=gateways,
                product_schemas=product_schemas,
                apply_runtime_overrides=self._runtime_state.apply_to_device,
                rooms=self.rooms,
                areas=self.areas,
            )
            apply_identity_scope_to_device_maps(
                entry_data=self.entry_data,
                house_id=self.house_id,
                devices=data,
                gateways=gateway_data,
            )

            self.devices = data
            self.gateways = gateway_data
            self._update_topology_generation()

            _LOGGER.debug(
                "Updated %s devices, %s gateways, %s areas, %s rooms, "
                "%s groups, %s houses, %s scenes",
                len(data),
                len(gateway_data),
                len(self.areas),
                len(self.rooms),
                len(self.groups),
                len(self.houses),
                len(self.scenes),
            )
            return data

        except AuthenticationError:
            _LOGGER.warning("Authentication failed while updating Yeelight Pro data")
            raise ConfigEntryAuthFailed("Yeelight Pro authentication failed") from None
        except ConnectionError as err:
            raise self._update_failed("Connection error", err) from None
        except Exception as err:
            raise self._update_failed("Error communicating with API", err) from None

    async def _async_fetch_auxiliary_data(self) -> None:
        """获取 areas/rooms/groups/houses/scenes 辅助数据."""
        if self.client is None:
            return
        auxiliary = await async_fetch_auxiliary_data(
            self.client,
            self.house_id,
            AuxiliaryData(
                areas=self.areas,
                rooms=self.rooms,
                groups=self.groups,
                houses=self.houses,
                scenes=self.scenes,
            ),
        )
        self.areas = auxiliary.areas
        self.rooms = auxiliary.rooms
        self.groups = auxiliary.groups
        self.houses = auxiliary.houses
        self.scenes = auxiliary.scenes

    async def _async_get_gateways(
        self,
        client: YeelightProClient,
    ) -> list[dict[str, Any]]:
        """获取网关列表，普通失败降级为空列表."""
        try:
            return await client.get_gateways(self.house_id)
        except AuthenticationError:
            raise
        except Exception as err:
            _LOGGER.warning("Failed to fetch gateways: %s", safe_error_summary(err))
            return []

    def _update_failed(self, message: str, err: Exception) -> UpdateFailed:
        """Build a sanitized Home Assistant update error."""
        summary = safe_error_summary(err)
        _LOGGER.error("%s while updating Yeelight Pro data: %s", message, summary)
        return UpdateFailed(f"{message}: {summary}")

    async def _async_get_product_schemas(
        self,
        client: YeelightProClient,
        items: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """获取产品 schema，优先复用缓存以稳定实体投影."""
        product_ids = product_ids_from_items(items)
        return await self._product_schema_cache.async_get_with_fallback(
            product_ids,
            client.get_product_schemas,
            force_refresh=self._force_product_schema_refresh,
        )

    async def async_request_product_schema_refresh(self) -> None:
        """手动刷新时强制重新拉取当前产品 schema."""
        self._force_product_schema_refresh = True
        try:
            await self.async_refresh()
        finally:
            self._force_product_schema_refresh = False

    async def _async_refresh_coordinator_data(self) -> None:
        """由 LAN 拓扑推送触发的 coordinator 数据刷新。"""
        _LOGGER.debug("LAN topology push: refreshing coordinator data")
        await self.async_refresh()

    def _update_topology_generation(self) -> None:
        """仅在实体/设备拓扑变化时递增代数."""
        self._topology_tracker.update(
            devices=self.devices,
            gateways=self.gateways,
            areas=self.areas,
            rooms=self.rooms,
            groups=self.groups,
            houses=self.houses,
            scenes=self.scenes,
        )

    def get_device(self, device_id: int | str) -> dict[str, Any] | None:
        """获取设备数据."""
        try:
            normalized_device_id = int(device_id)
        except (TypeError, ValueError):
            normalized_device_id = None
        if normalized_device_id is not None:
            return self.devices.get(normalized_device_id)
        return next(
            (
                payload
                for payload in self.devices.values()
                if str(payload.get("device_id") or payload.get("id")) == str(device_id)
            ),
            None,
        )

    def get_gateway_devices(self) -> Dict[int, Dict[str, Any]]:
        """获取网关设备."""
        return self.gateways.copy()

    @property
    def topology_generation(self) -> int:
        """返回拓扑代数."""
        return self._topology_tracker.generation

    @property
    def topology_diff_summary(self) -> TopologyDiffSummary:
        """返回最近一次拓扑变化的脱敏分类摘要."""
        return self._topology_tracker.diff_summary

    @property
    def product_schema_cache_size(self) -> int:
        """返回当前内存产品 schema 缓存数量."""
        return self._product_schema_cache.size
