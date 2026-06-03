"""Yeelight Pro 数据协调器.

负责定期更新设备数据并协调各个平台。
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DEFAULT_SCAN_INTERVAL, DEVICE_EVENT_TYPE, DOMAIN
from .client import YeelightProClient
from .exceptions import ConnectionError, TokenExpiredError

_LOGGER = logging.getLogger(__name__)


class YeelightProCoordinator(DataUpdateCoordinator):
    """Yeelight Pro 数据协调器."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: YeelightProClient,
        house_id: int,
    ):
        """初始化协调器."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.house_id = house_id
        self.devices: Dict[int, Dict[str, Any]] = {}
        self.gateways: Dict[int, Dict[str, Any]] = {}
        self._runtime_state_overrides: Dict[int, Dict[str, Any]] = {}
        self._topology_generation = 0

    async def _async_update_data(self) -> Dict[int, Any]:
        """从 API 获取数据."""
        try:
            # 获取设备列表
            devices = await self.client.get_devices(self.house_id)

            # 获取网关列表（可选）
            try:
                gateways = await self.client.get_gateways(self.house_id)
            except Exception as err:
                gateways = []
                _LOGGER.warning("Failed to fetch gateways: %s", err)

            # 获取产品规格（可选）
            try:
                product_ids = [
                    item.get("pid")
                    for item in [*devices, *gateways]
                    if isinstance(item, Mapping) and item.get("pid")
                ]
                product_schemas = await self.client.get_product_schemas(product_ids)
            except Exception as err:
                product_schemas = {}
                _LOGGER.warning("Failed to fetch product schemas: %s", err)

            # 转换为字典格式
            data = {}
            for device in devices:
                device_id = device.get("id")
                if device_id:
                    normalized = self._normalize_device(device, product_schemas)
                    data[device_id] = self._apply_runtime_state_overrides(normalized)

            gateway_data = {}
            for gateway in gateways:
                gateway_id = gateway.get("id")
                if gateway_id:
                    normalized = self._normalize_device(gateway, product_schemas)
                    gateway_data[gateway_id] = normalized
                    data[gateway_id] = normalized

            self.devices = data
            self.gateways = gateway_data
            self._topology_generation += 1

            _LOGGER.debug("Updated %s devices and %s gateways", len(data), len(gateway_data))
            return data

        except TokenExpiredError:
            _LOGGER.error("Access token expired, please reconfigure the integration")
            raise UpdateFailed("Token expired")
        except ConnectionError as err:
            _LOGGER.error("Connection error: %s", err)
            raise UpdateFailed(f"Connection error: {err}")
        except Exception as err:
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}")

    def _normalize_device(
        self,
        device: dict[str, Any],
        product_schemas: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        """规范化设备数据."""
        normalized = dict(device)

        # 添加产品规格
        pid = device.get("pid")
        if pid and pid in product_schemas:
            normalized["product_schema"] = product_schemas[pid]

        return normalized

    def _apply_runtime_state_overrides(
        self,
        device: dict[str, Any],
    ) -> dict[str, Any]:
        """应用运行时状态覆盖."""
        device_id = device.get("id")
        if device_id in self._runtime_state_overrides:
            overrides = self._runtime_state_overrides[device_id]
            if "params" in overrides:
                device.setdefault("params", {}).update(overrides["params"])
            if "online" in overrides:
                device["online"] = overrides["online"]
        return device

    def get_device(self, device_id: int) -> dict[str, Any] | None:
        """获取设备数据."""
        return self.devices.get(device_id)

    def get_gateway_devices(self) -> Dict[int, Dict[str, Any]]:
        """获取网关设备."""
        return self.gateways.copy()

    async def async_control_device(
        self,
        device_id: int,
        params: dict[str, Any],
        duration: int = 500,
    ) -> bool:
        """控制设备."""
        device = self.get_device(device_id)
        if not device:
            _LOGGER.error("Device %s not found", device_id)
            return False

        gateway_id = device.get("gatewayDeviceId")
        if not gateway_id:
            _LOGGER.error("Device %s has no gateway", device_id)
            return False

        try:
            await self.client.control_device(device_id, gateway_id, params, duration)

            # 乐观更新
            self._runtime_state_overrides.setdefault(device_id, {}).update({
                "params": params,
            })

            # 通知监听器
            self.async_update_listeners()

            return True
        except Exception as err:
            _LOGGER.error("Failed to control device %s: %s", device_id, err)
            return False

    async def async_toggle_device(
        self,
        device_id: int,
        properties: list[str],
    ) -> bool:
        """切换设备属性."""
        device = self.get_device(device_id)
        if not device:
            _LOGGER.error("Device %s not found", device_id)
            return False

        gateway_id = device.get("gatewayDeviceId")
        if not gateway_id:
            _LOGGER.error("Device %s has no gateway", device_id)
            return False

        try:
            await self.client.toggle_device(device_id, gateway_id, properties)
            await self.async_request_refresh()
            return True
        except Exception as err:
            _LOGGER.error("Failed to toggle device %s: %s", device_id, err)
            return False

    async def async_execute_scene(self, scene_id: str) -> bool:
        """执行场景."""
        try:
            await self.client.execute_scene(scene_id)
            return True
        except Exception as err:
            _LOGGER.error("Failed to execute scene %s: %s", scene_id, err)
            return False

    @property
    def topology_generation(self) -> int:
        """返回拓扑代数."""
        return self._topology_generation
