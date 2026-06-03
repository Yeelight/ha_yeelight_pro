"""Cover platform for Yeelight Pro integration."""
import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .projector.cover import HACoverProjection, project_cover

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yeelight Pro cover platform."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    covers = []
    for device_id, device_data in coordinator.data.items():
        if project_cover(device_data, domain=DOMAIN) is not None:
            covers.append(YeelightProCover(coordinator, device_id))

    if covers:
        async_add_entities(covers)
        _LOGGER.info(f"Added {len(covers)} cover entities")


class YeelightProCover(CoordinatorEntity, CoverEntity):
    """Representation of a Yeelight Pro Cover."""

    def __init__(self, coordinator: YeelightProCoordinator, device_id: int):
        """Initialize the cover."""
        super().__init__(coordinator)
        self._device_id = device_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id if projection is not None else f"{DOMAIN}_{device_id}_cover"
        )
        self._attr_has_entity_name = True
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        )

    @property
    def _projection(self) -> HACoverProjection | None:
        """Return the latest projected cover view."""
        return project_cover(self.coordinator.get_device(self._device_id), domain=DOMAIN)

    @property
    def name(self) -> str | None:
        """Return the name of the cover."""
        projection = self._projection
        if projection is not None:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        return device_data.get("name", f"Cover {self._device_id}")

    @property
    def available(self) -> bool:
        """Return if the cover is available."""
        projection = self._projection
        if projection is not None:
            return projection.available
        return False

    @property
    def device_info(self) -> dict[str, Any] | None:
        """Return device information."""
        projection = self._projection
        if projection is not None:
            return projection.device_info
        return None

    @property
    def device_class(self):
        """Return the device class."""
        projection = self._projection
        if projection is not None:
            return projection.device_class
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        projection = self._projection
        if projection is not None:
            return projection.icon
        return None

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover."""
        projection = self._projection
        if projection is not None:
            return projection.current_cover_position
        return None

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        projection = self._projection
        if projection is not None:
            return projection.is_closed
        return None

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        projection = self._projection
        if projection is not None:
            return projection.is_opening
        return False

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        projection = self._projection
        if projection is not None:
            return projection.is_closing
        return False

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        try:
            await self.coordinator.async_control_device(self._device_id, {"tp": 100})
        except YeelightProError as err:
            raise HomeAssistantError(
                f"打开窗帘失败: 设备 {self._device_id}: {err}"
            ) from err

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        try:
            await self.coordinator.async_control_device(self._device_id, {"tp": 0})
        except YeelightProError as err:
            raise HomeAssistantError(
                f"关闭窗帘失败: 设备 {self._device_id}: {err}"
            ) from err

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get("position", 0)
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {"tp": max(0, min(100, int(position)))},
            )
        except YeelightProError as err:
            raise HomeAssistantError(
                f"设置窗帘位置失败: 设备 {self._device_id}, 位置 {position}: {err}"
            ) from err
