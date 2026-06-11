"""Yeelight Pro sensor 平台."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .device_display import suggested_entity_object_id
from .dynamic_entities import async_track_dynamic_entities
from .entity_device_id import source_device_id
from .entity_category import ha_entity_category
from .projector.sensor import HASensorProjection, project_sensors

_LOGGER = logging.getLogger(__name__)

# 传感器设备类映射
SENSOR_DEVICE_CLASS_MAP = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "illuminance": SensorDeviceClass.ILLUMINANCE,
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
}
SENSOR_STATE_CLASS_MAP = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro sensor 平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_sensor_entities,
        logger=_LOGGER,
        platform_name="sensor",
    )


def _iter_sensor_entities(coordinator: YeelightProCoordinator) -> list["YeelightProSensor"]:
    """按当前拓扑生成 sensor 实体候选."""
    sensors: list[YeelightProSensor] = []
    for device_key, device_data in coordinator.data.items():
        device_id = source_device_id(device_key, device_data)
        projections = project_sensors(
            device_data,
            domain=DOMAIN,
            hide_unknown_entities=coordinator.hide_unknown_entities,
        )
        for projection in projections:
            sensors.append(
                YeelightProSensor(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )
    return sensors


class YeelightProSensor(CoordinatorEntity, SensorEntity):
    """Yeelight Pro 传感器实体."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int | str,
        *,
        component_id: str,
    ) -> None:
        """初始化传感器实体."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{device_id}_{component_id}"
        )

    @property
    def _projection(self) -> HASensorProjection | None:
        """返回最新的传感器投影视图."""
        device = self.coordinator.get_device(self._device_id)
        if device is None:
            return None
        projections = project_sensors(
            device,
            domain=DOMAIN,
            hide_unknown_entities=self.coordinator.hide_unknown_entities,
        )
        return next(
            (item for item in projections if item.component_id == self._component_id),
            None,
        )

    @property
    def name(self) -> str | None:
        """返回传感器名称."""
        projection = self._projection
        if projection is not None:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        if device_data is not None:
            return device_data.get("name", f"Sensor {self._device_id}")
        return f"Sensor {self._device_id}"

    @property
    def suggested_object_id(self) -> str | None:
        """返回 HA 首次注册时使用的友好实体 ID 建议."""
        return suggested_entity_object_id(
            self.coordinator.get_device(self._device_id),
            entity_name=self.name,
            fallback_id=self._device_id,
        )

    @property
    def available(self) -> bool:
        """返回传感器是否可用."""
        projection = self._projection
        if projection is not None:
            return projection.available
        return False

    @property
    def device_info(self) -> dict[str, Any] | None:
        """返回设备信息."""
        projection = self._projection
        if projection is not None:
            return projection.device_info
        return None

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """返回设备类."""
        projection = self._projection
        if projection is None:
            return None
        if projection.device_class is None:
            return None
        return SENSOR_DEVICE_CLASS_MAP.get(projection.device_class)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """返回原生计量单位."""
        projection = self._projection
        if projection is None:
            return None
        return projection.native_unit_of_measurement

    @property
    def state_class(self) -> SensorStateClass | None:
        """返回长期统计状态类."""
        projection = self._projection
        if projection is None or projection.state_class is None:
            return None
        return SENSOR_STATE_CLASS_MAP.get(projection.state_class)

    @property
    def entity_category(self):
        """返回实体分类，用于 HA 设备页分组."""
        projection = self._projection
        if projection is None:
            return None
        return ha_entity_category(projection.entity_category)

    @property
    def icon(self) -> str | None:
        """返回传感器图标."""
        projection = self._projection
        if projection is None:
            return None
        return projection.icon

    @property
    def native_value(self) -> Any:
        """返回传感器状态值."""
        projection = self._projection
        if projection is None:
            return None
        return projection.native_value
