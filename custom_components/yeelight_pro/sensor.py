"""Yeelight Pro sensor 平台."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .analytics_runtime import ANALYTICS_METRIC_KEYS
from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .dynamic_entities import async_track_dynamic_entities
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
    if getattr(coordinator, "analytics_runtime_enabled", False):
        sensors.extend(
            YeelightProAnalyticsSensor(coordinator, metric_key)
            for metric_key in ANALYTICS_METRIC_KEYS
        )
    for device_id, device_data in coordinator.data.items():
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


class YeelightProAnalyticsSensor(CoordinatorEntity, SensorEntity):
    """Yeelight Pro 数据分析聚合传感器."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        metric_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._metric_key = metric_key
        self._attr_unique_id = f"{DOMAIN}_{coordinator.house_id}_analytics_{metric_key}"
        self._attr_translation_key = f"analytics_{metric_key}"

    @property
    def native_value(self) -> Any:
        """返回最新聚合指标值."""
        return self.coordinator.analytics_summary().get(self._metric_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回脱敏刷新元数据."""
        summary = self.coordinator.analytics_summary()
        return {
            "last_endpoint": summary.get("last_endpoint"),
            "last_refreshed_at": summary.get("last_refreshed_at"),
            "retention_days": summary.get("retention_days"),
            "history_size": summary.get("history_size"),
        }

    @property
    def native_unit_of_measurement(self) -> str | None:
        """返回聚合指标单位."""
        if self._metric_key in {"energy_used_kwh", "energy_saved_kwh"}:
            return "kWh"
        return None

    @property
    def state_class(self) -> SensorStateClass | None:
        """数据分析聚合值作为测量值展示."""
        return SensorStateClass.MEASUREMENT

    @property
    def icon(self) -> str | None:
        """返回指标图标."""
        if self._metric_key.startswith("alarm_"):
            return "mdi:alert-outline"
        if self._metric_key.startswith("energy_"):
            return "mdi:lightning-bolt-outline"
        return "mdi:gesture-tap"


class YeelightProSensor(CoordinatorEntity, SensorEntity):
    """Yeelight Pro 传感器实体."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int,
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
        projections = project_sensors(
            self.coordinator.get_device(self._device_id),
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
