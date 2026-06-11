"""Binary sensor platform for Yeelight Pro integration."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
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
from .projector.binary_sensor import (
    HABinarySensorProjection,
    project_binary_sensors,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yeelight Pro binary sensor platform."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_binary_sensor_entities,
        logger=_LOGGER,
        platform_name="binary sensor",
    )


def _iter_binary_sensor_entities(
    coordinator: YeelightProCoordinator,
) -> list["YeelightProBinarySensor"]:
    """按当前拓扑生成 binary sensor 实体候选."""
    binary_sensors: list[YeelightProBinarySensor] = []
    for device_key, device_data in coordinator.data.items():
        device_id = source_device_id(device_key, device_data)
        projections = project_binary_sensors(device_data, domain=DOMAIN)
        for projection in projections:
            binary_sensors.append(
                YeelightProBinarySensor(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )
    return binary_sensors


BINARY_SENSOR_DEVICE_CLASS_MAP = {
    "motion": BinarySensorDeviceClass.MOTION,
    "door": BinarySensorDeviceClass.DOOR,
    "tamper": BinarySensorDeviceClass.TAMPER,
    "battery_charging": BinarySensorDeviceClass.BATTERY_CHARGING,
}


class YeelightProBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Yeelight Pro Binary Sensor."""

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int | str,
        *,
        component_id: str,
    ):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{device_id}_{component_id}"
        )
        self._attr_has_entity_name = True

    @property
    def _projection(self) -> HABinarySensorProjection | None:
        """Return the latest projected binary-sensor view."""
        device = self.coordinator.get_device(self._device_id)
        if device is None:
            return None
        projections = project_binary_sensors(
            device,
            domain=DOMAIN,
        )
        return next(
            (item for item in projections if item.component_id == self._component_id),
            None,
        )

    @property
    def name(self) -> str | None:
        """Return the name of the binary sensor."""
        projection = self._projection
        if projection is not None:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        if device_data is not None:
            return device_data.get("name", f"Binary Sensor {self._device_id}")
        return f"Binary Sensor {self._device_id}"

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
        """Return if the binary sensor is available."""
        projection = self._projection
        if projection is not None:
            return projection.available
        return False

    @property
    def device_info(self):
        """Return device information."""
        projection = self._projection
        if projection is not None:
            return projection.device_info
        return None

    @property
    def device_class(self):
        """Return the device class."""
        projection = self._projection
        if projection is None:
            return None
        return BINARY_SENSOR_DEVICE_CLASS_MAP.get(projection.device_class)

    @property
    def icon(self):
        """Return the icon."""
        projection = self._projection
        if projection is None:
            return None
        return projection.icon

    @property
    def entity_category(self):
        """Return HA entity category for device page grouping."""
        projection = self._projection
        if projection is None:
            return None
        return ha_entity_category(projection.entity_category)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        projection = self._projection
        if projection is None:
            return None
        return projection.is_on
