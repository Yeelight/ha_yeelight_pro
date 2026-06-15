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
from .device_display import suggested_entity_object_id
from .dynamic_entities import async_track_dynamic_entities
from .entity_device_id import source_device_id
from .entity_errors import raise_service_error
from .identity import device_entity_unique_id
from .projector.cover import HACoverProjection, project_covers

_LOGGER = logging.getLogger(__name__)
ERROR_COVER_PROJECTION_UNAVAILABLE = "无法解析窗帘投影"
_COVER_BASE_FEATURES = (
    CoverEntityFeature.OPEN
    | CoverEntityFeature.CLOSE
    | CoverEntityFeature.SET_POSITION
)
_COVER_STOP_ACTION = {"motorAdjust": {"type": "pause"}}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Yeelight Pro cover platform."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_cover_entities,
        logger=_LOGGER,
        platform_name="cover",
    )


def _iter_cover_entities(coordinator: YeelightProCoordinator) -> list["YeelightProCover"]:
    """按当前拓扑生成 cover 实体候选."""
    covers: list[YeelightProCover] = []
    for device_key, device_data in coordinator.data.items():
        device_id = source_device_id(device_key, device_data)
        projections = project_covers(device_data, domain=DOMAIN)
        _LOGGER.debug(
            "Cover candidates projected: device_id=%s projection_count=%d "
            "component_ids=%s",
            device_id,
            len(projections),
            [item.component_id for item in projections],
        )
        for projection in projections:
            covers.append(
                YeelightProCover(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )
    return covers


class YeelightProCover(CoordinatorEntity, CoverEntity):
    """Representation of a Yeelight Pro Cover."""

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int | str,
        *,
        component_id: str | None = None,
    ):
        """Initialize the cover."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else device_entity_unique_id(
                coordinator,
                device_id,
                component_id or "cover",
            )
        )
        self._attr_has_entity_name = True

    @property
    def _projection(self) -> HACoverProjection | None:
        """Return the latest projected cover view."""
        device = self.coordinator.get_device(self._device_id)
        if device is None:
            return None
        projections = project_covers(device, domain=DOMAIN)
        if self._component_id is None:
            return projections[0] if projections else None
        return next(
            (item for item in projections if item.component_id == self._component_id),
            None,
        )

    @property
    def name(self) -> str | None:
        """Return the name of the cover."""
        projection = self._projection
        if projection is not None:
            return projection.name
        return "窗帘"

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

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Return cover features currently supported by this entry."""
        features = _COVER_BASE_FEATURES
        can_control_action = getattr(
            self.coordinator,
            "can_control_device_action",
            None,
        )
        if callable(can_control_action) and can_control_action() is True:
            features |= CoverEntityFeature.STOP
        return features

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._async_set_target_position("cover.open_cover", 100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._async_set_target_position("cover.close_cover", 0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get("position", 0)
        await self._async_set_target_position("cover.set_cover_position", position)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Pause cover movement through the documented LAN motor action."""
        projection = self._projection
        if projection is None:
            _LOGGER.debug(
                "Skipping cover stop: device_id=%s component_id=%s reason=%s",
                self._device_id,
                self._component_id,
                "projection_unavailable",
            )
            raise HomeAssistantError(ERROR_COVER_PROJECTION_UNAVAILABLE)

        try:
            await self.coordinator.async_action_device(
                self._device_id,
                _COVER_STOP_ACTION,
            )
        except YeelightProError as err:
            raise_service_error("cover.stop_cover", err)

    async def _async_set_target_position(self, action: str, position: Any) -> None:
        """下发窗帘目标位置，按 projection 选择组件级控制键."""
        projection = self._projection
        if projection is None:
            _LOGGER.debug(
                "Skipping cover control: device_id=%s component_id=%s action=%s "
                "reason=%s",
                self._device_id,
                self._component_id,
                action,
                "projection_unavailable",
            )
            raise HomeAssistantError(ERROR_COVER_PROJECTION_UNAVAILABLE)

        target = max(0, min(100, int(position)))
        key = projection.target_position_key
        _LOGGER.debug(
            "Cover control request: device_id=%s component_id=%s action=%s "
            "control_key=%s target_position=%s",
            self._device_id,
            projection.component_id,
            action,
            key,
            target,
        )
        try:
            await self.coordinator.async_control_device(self._device_id, {key: target})
        except YeelightProError as err:
            raise_service_error(action, err)
