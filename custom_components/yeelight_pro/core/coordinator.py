"""Yeelight Pro 数据协调器.

负责定期更新设备数据并协调各个平台。
同时管理 rooms/groups/scenes/automations 等辅助数据，避免平台绕过 coordinator 直接调 API。
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DEFAULT_SCAN_INTERVAL, DEVICE_EVENT_TYPE, DOMAIN
from .client import YeelightProClient
from .exceptions import (
    CommandError,
    ConnectionError,
    DeviceNotFoundError,
    YeelightProError,
)

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
        # 辅助数据：平台 setup 时读取，不再直接调 API
        self.rooms: list[dict[str, Any]] = []
        self.groups: list[dict[str, Any]] = []
        self.scenes: list[dict[str, Any]] = []
        self.automations: list[dict[str, Any]] = []
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

            # 获取辅助数据（rooms/groups/scenes/automations），失败不阻断主流程
            await self._async_fetch_auxiliary_data()

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

            _LOGGER.debug(
                "Updated %s devices, %s gateways, %s rooms, %s groups, "
                "%s scenes, %s automations",
                len(data),
                len(gateway_data),
                len(self.rooms),
                len(self.groups),
                len(self.scenes),
                len(self.automations),
            )
            return data

        except ConnectionError as err:
            _LOGGER.error("Connection error: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _async_fetch_auxiliary_data(self) -> None:
        """获取 rooms/groups/scenes/automations 辅助数据.

        每个数据源独立 try/except，任一失败不阻断其他数据的获取。
        """
        try:
            self.rooms = await self.client.get_rooms(self.house_id)
        except Exception as err:
            _LOGGER.warning("Failed to fetch rooms: %s", err)

        try:
            self.groups = await self.client.get_groups(self.house_id)
        except Exception as err:
            _LOGGER.warning("Failed to fetch groups: %s", err)

        try:
            self.scenes = await self.client.get_scenes(self.house_id)
        except Exception as err:
            _LOGGER.warning("Failed to fetch scenes: %s", err)

        try:
            self.automations = await self.client.get_automations(self.house_id)
        except Exception as err:
            _LOGGER.warning("Failed to fetch automations: %s", err)

    def _normalize_device(
        self,
        device: dict[str, Any],
        product_schemas: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        """规范化设备数据.

        将 open API 格式转换为 projector 期望的格式。
        新 API 返回: {id, name, category, nodeType, properties, roomId, ...}
        Projector 期望: {device_id, name, type, online, params, ...}
        """
        normalized = dict(device)

        # 兼容新 API 格式：category → type（映射 IoT 品类到 HA 设备类型）
        if "category" in normalized and "type" not in normalized:
            category = normalized["category"]
            # IoT 品类到 HA 设备类型的映射
            CATEGORY_TYPE_MAP = {
                "light": "light",
                "relay_switch": "switch",
                "curtain": "cover",
                "human_sensor": "binary_sensor",
                "contact_sensor": "binary_sensor",
                "light_sensor": "sensor",
                "temp_control": "climate",
                "scene_panel": "event",
                "gateway": "gateway",
            }
            normalized["type"] = CATEGORY_TYPE_MAP.get(category, category)

        # 兼容新 API 格式：id → device_id
        if "id" in normalized and "device_id" not in normalized:
            normalized["device_id"] = normalized["id"]

        # 兼容新 API 格式：properties → params
        if "properties" in normalized and "params" not in normalized:
            params = {}
            online = True
            for prop in normalized.get("properties", []):
                prop_id = prop.get("propId")
                value = prop.get("value")
                if prop_id == "o":
                    online = bool(value) if value is not None else True
                elif prop_id and value is not None:
                    params[prop_id] = value
            normalized["params"] = params
            normalized["online"] = online
        elif "online" not in normalized:
            normalized["online"] = True

        # 添加产品规格
        pid = normalized.get("pid")
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
    ) -> None:
        """控制设备.

        失败时抛出 HomeAssistantError 子类，实体层捕获后向 HA 报告。
        """
        device = self.get_device(device_id)
        if not device:
            raise DeviceNotFoundError(f"Device {device_id} not found")

        try:
            # 使用 open API，不需要 gateway_id
            await self.client.control_device(device_id, 0, params, duration)
        except YeelightProError:
            raise
        except Exception as err:
            raise CommandError(f"Failed to control device {device_id}: {err}") from err

        # 乐观更新
        self._runtime_state_overrides.setdefault(device_id, {}).update({
            "params": params,
        })

        # 通知监听器
        self.async_update_listeners()

    async def async_toggle_device(
        self,
        device_id: int,
        properties: list[str],
    ) -> None:
        """切换设备属性.

        失败时抛出异常，实体层捕获后向 HA 报告。
        """
        device = self.get_device(device_id)
        if not device:
            raise DeviceNotFoundError(f"Device {device_id} not found")

        try:
            # 使用 open API，不需要 gateway_id
            await self.client.toggle_device(device_id, 0, properties)
        except YeelightProError:
            raise
        except Exception as err:
            raise CommandError(f"Failed to toggle device {device_id}: {err}") from err

        await self.async_request_refresh()

    async def async_execute_scene(self, scene_id: str) -> None:
        """执行场景.

        失败时抛出异常，实体层捕获后向 HA 报告。
        """
        try:
            await self.client.execute_scene(scene_id)
        except YeelightProError:
            raise
        except Exception as err:
            raise CommandError(f"Failed to execute scene {scene_id}: {err}") from err

    async def async_trigger_automation(self, automation_id: str) -> None:
        """手动触发自动化.

        失败时抛出异常，实体层捕获后向 HA 报告。
        """
        try:
            await self.client.trigger_automation(automation_id)
        except YeelightProError:
            raise
        except Exception as err:
            raise CommandError(
                f"Failed to trigger automation {automation_id}: {err}"
            ) from err

    async def async_control_group(
        self,
        group_id: str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """控制灯组.

        失败时抛出异常，实体层捕获后向 HA 报告。
        """
        try:
            await self.client.control_group(group_id, params, duration)
        except YeelightProError:
            raise
        except Exception as err:
            raise CommandError(
                f"Failed to control group {group_id}: {err}"
            ) from err

    @property
    def topology_generation(self) -> int:
        """返回拓扑代数."""
        return self._topology_generation
