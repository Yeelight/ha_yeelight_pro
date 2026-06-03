"""扫地机器人平台，Yeelight Pro 集成.

提供扫地机器人的清扫控制、状态查询和电池电量管理。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    VacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .projector.vacuum import HAVacuumProjection, project_vacuum

_LOGGER = logging.getLogger(__name__)

# HA 状态字符串 → 内部状态映射
_STATE_MAP: dict[str, str] = {
    "cleaning": STATE_CLEANING,
    "charging": STATE_DOCKED,
    "charged": STATE_DOCKED,
    "docked": STATE_DOCKED,
    "idle": STATE_IDLE,
    "standby": STATE_IDLE,
    "returning": STATE_RETURNING,
    "paused": STATE_PAUSED,
    "error": STATE_ERROR,
    "fault": STATE_ERROR,
    "manual": STATE_IDLE,
    "sleeping": STATE_IDLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro 扫地机器人平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    vacuums: list[YeelightProVacuum] = []
    for device_id, device_data in coordinator.data.items():
        if project_vacuum(device_data, domain=DOMAIN) is not None:
            vacuums.append(YeelightProVacuum(coordinator, device_id))

    if vacuums:
        async_add_entities(vacuums)
        _LOGGER.info("已添加 %s 个 vacuum 实体", len(vacuums))


class YeelightProVacuum(CoordinatorEntity, VacuumEntity):
    """Yeelight Pro 扫地机器人实体."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int,
    ) -> None:
        """初始化扫地机器人实体."""
        super().__init__(coordinator)
        self._device_id = device_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{device_id}_vacuum"
        )
        self._attr_supported_features = (
            projection.supported_features
            if projection is not None
            else self._default_features()
        )

    @property
    def _projection(self) -> HAVacuumProjection | None:
        """返回最新的扫地机器人投影视图."""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None
        return project_vacuum(device, domain=DOMAIN)

    @property
    def icon(self) -> str | None:
        """返回前端图标."""
        projection = self._projection
        if projection is not None and projection.icon:
            return projection.icon
        return "mdi:robot-vacuum"

    @property
    def device_info(self) -> dict[str, Any]:
        """返回设备信息."""
        projection = self._projection
        if projection is not None and projection.device_info is not None:
            return projection.device_info
        return {}

    @property
    def name(self) -> str | None:
        """返回扫地机器人名称."""
        projection = self._projection
        if projection is not None and projection.name:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        if device_data:
            return device_data.get("name", f"Vacuum {self._device_id}")
        return f"Vacuum {self._device_id}"

    @property
    def available(self) -> bool:
        """返回扫地机器人是否可用."""
        projection = self._projection
        if projection is not None:
            return projection.available
        device_data = self.coordinator.get_device(self._device_id)
        return device_data.get("online", False) if device_data else False

    @property
    def battery_level(self) -> int | None:
        """返回电池电量百分比."""
        projection = self._projection
        return projection.battery_level if projection is not None else None

    @property
    def state(self) -> str | None:
        """返回当前真空状态."""
        projection = self._projection
        if projection is None:
            return None
        raw_status = projection.status
        return _STATE_MAP.get(raw_status, STATE_IDLE)

    @property
    def fan_speed(self) -> str | None:
        """返回当前吸力档位."""
        projection = self._projection
        if projection is None or projection.fan_speed is None:
            return None
        # 将数字档位映射为名称
        speed_index = max(0, min(projection.fan_speed, len(projection.fan_speed_list) - 1))
        return projection.fan_speed_list[speed_index]

    @property
    def fan_speed_list(self) -> list[str]:
        """返回可选吸力档位列表."""
        projection = self._projection
        if projection is not None:
            return projection.fan_speed_list
        return ["low", "medium", "high", "max"]

    async def async_start(self) -> None:
        """开始清扫."""
        success = await self.coordinator.async_control_device(
            self._device_id, {"action": "start"}
        )
        if not success:
            _LOGGER.error("启动清扫失败: 设备 %s", self._device_id)

    async def async_pause(self) -> None:
        """暂停清扫."""
        success = await self.coordinator.async_control_device(
            self._device_id, {"action": "pause"}
        )
        if not success:
            _LOGGER.error("暂停清扫失败: 设备 %s", self._device_id)

    async def async_stop(self, **kwargs: Any) -> None:
        """停止清扫."""
        success = await self.coordinator.async_control_device(
            self._device_id, {"action": "stop"}
        )
        if not success:
            _LOGGER.error("停止清扫失败: 设备 %s", self._device_id)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """返回充电座."""
        success = await self.coordinator.async_control_device(
            self._device_id, {"action": "return_to_base"}
        )
        if not success:
            _LOGGER.error("返回充电座失败: 设备 %s", self._device_id)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """设置吸力档位."""
        if fan_speed not in self.fan_speed_list:
            _LOGGER.error("无效的吸力档位: %s，可选项: %s", fan_speed, self.fan_speed_list)
            return
        speed_index = self.fan_speed_list.index(fan_speed)
        success = await self.coordinator.async_control_device(
            self._device_id, {"fan_speed": speed_index}
        )
        if not success:
            _LOGGER.error("设置吸力档位失败: 设备 %s", self._device_id)

    @staticmethod
    def _default_features() -> int:
        """返回默认支持的功能标志位."""
        return (
            VacuumEntityFeature.START
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.FAN_SPEED
            | VacuumEntityFeature.BATTERY
            | VacuumEntityFeature.STATUS
        )
