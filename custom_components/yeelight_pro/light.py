"""灯光平台，Yeelight Pro 集成。"""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .device_display import suggested_entity_object_id
from .entity_device_id import source_device_id
from .dynamic_entities import async_track_dynamic_entities
from .entity_errors import raise_service_error
from .light_group import YeelightProGroupLight
from .projector.light import (
    HALightProjection,
    NumericRange,
    project_lights,
)

_LOGGER = logging.getLogger(__name__)

try:
    from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN
except ImportError:  # pragma: no cover - 兼容旧版 HA
    from homeassistant.components.light import ATTR_COLOR_TEMP as ATTR_COLOR_TEMP_KELVIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """初始化 Yeelight Pro 灯光平台。"""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    _LOGGER.debug(
        "Light platform init: entry=%s coord_id=%s data_keys=%d first_key=%s",
        config_entry.entry_id[:12],
        id(coordinator),
        len(coordinator.data),
        next(iter(coordinator.data), None),
    )

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_light_entities,
        logger=_LOGGER,
        platform_name="light",
    )


def _iter_light_entities(coordinator: YeelightProCoordinator) -> list[LightEntity]:
    """按当前拓扑生成灯光实体候选。"""
    lights: list[LightEntity] = []
    for device_key, device_data in coordinator.data.items():
        device_id = source_device_id(device_key, device_data)
        projections = project_lights(device_data, domain=DOMAIN)
        _LOGGER.debug(
            "Light candidate: key=%s device_id=%s projections=%d params=%s ha_platform=%s",
            device_key,
            device_id,
            len(projections),
            device_data.get("params"),
            device_data.get("ha_platform"),
        )
        for projection in projections:
            lights.append(
                YeelightProLight(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )

    for group in coordinator.groups:
        group_id = group.get("id") or group.get("groupId")
        if group_id in (None, ""):
            continue
        lights.append(YeelightProGroupLight(coordinator, str(group_id)))
    return lights


class YeelightProLight(CoordinatorEntity, LightEntity):
    """Yeelight Pro 灯光实体。"""

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int | str,
        *,
        component_id: str | None = None,
    ) -> None:
        """初始化灯光实体。"""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{device_id}_{component_id or 'light'}"
        )
        self._attr_has_entity_name = True

    @property
    def _projection(self) -> HALightProjection | None:
        """返回最新的灯光投影视图。"""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None
        projections = project_lights(device, domain=DOMAIN)
        if self._component_id is None:
            return projections[0] if projections else None
        return next(
            (item for item in projections if item.component_id == self._component_id),
            None,
        )

    @property
    def icon(self) -> str | None:
        """返回前端图标。"""
        projection = self._projection
        if projection is not None:
            return projection.icon
        return "mdi:lightbulb"

    @property
    def device_info(self) -> Dict[str, Any]:
        """返回设备信息。"""
        projection = self._projection
        if projection is not None and projection.device_info is not None:
            return projection.device_info
        return {}

    @property
    def name(self) -> str | None:
        """返回灯光名称。"""
        projection = self._projection
        if projection is not None:
            return projection.name
        return None

    @property
    def suggested_object_id(self) -> str | None:
        """返回 HA 首次注册时使用的友好实体 ID 建议。"""
        return suggested_entity_object_id(
            self.coordinator.get_device(self._device_id),
            entity_name=self.name,
            fallback_id=self._device_id,
        )

    @property
    def available(self) -> bool:
        """返回灯光是否可用。"""
        projection = self._projection
        if projection is not None:
            return projection.available
        device_data = self.coordinator.get_device(self._device_id)
        return device_data.get("online", False) if device_data else False

    @property
    def is_on(self) -> bool:
        """返回灯光是否开启。"""
        projection = self._projection
        return projection.is_on if projection is not None else False

    @property
    def brightness(self) -> int | None:
        """返回灯光亮度（0..255）。"""
        projection = self._projection
        return projection.brightness if projection is not None else None

    @property
    def color_temp_kelvin(self) -> int | None:
        """返回色温（开尔文）。"""
        projection = self._projection
        if projection is None or projection.color_temp is None or projection.color_temp <= 0:
            return None
        return int(1000000 / projection.color_temp)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """返回 RGB 颜色值。"""
        projection = self._projection
        return projection.rgb_color if projection is not None else None

    @property
    def supported_color_modes(self) -> set:
        """返回支持的颜色模式集合。"""
        projection = self._projection
        if projection is not None:
            return projection.supported_color_modes
        return {ColorMode.ONOFF}

    @property
    def color_mode(self) -> str:
        """返回当前颜色模式。"""
        projection = self._projection
        if projection is not None:
            return projection.color_mode
        return ColorMode.ONOFF

    @property
    def min_color_temp_kelvin(self) -> int:
        """返回最暖色温（开尔文）。"""
        projection = self._projection
        if (
            projection is not None
            and projection.color_temp_range_kelvin is not None
            and projection.color_temp_range_kelvin.min is not None
        ):
            return projection.color_temp_range_kelvin.min
        return 2700

    @property
    def max_color_temp_kelvin(self) -> int:
        """返回最冷色温（开尔文）。"""
        projection = self._projection
        if (
            projection is not None
            and projection.color_temp_range_kelvin is not None
            and projection.color_temp_range_kelvin.max is not None
        ):
            return projection.color_temp_range_kelvin.max
        return 6500

    async def async_turn_on(self, **kwargs: Any) -> None:
        """开启灯光。"""
        projection = self._projection
        params: dict[str, Any] = {
            (projection.power_key if projection is not None else "p"): True
        }

        # 设置亮度
        if ATTR_BRIGHTNESS in kwargs:
            brightness_key = projection.brightness_key if projection is not None else "l"
            params[brightness_key] = self._brightness_from_ha(
                kwargs[ATTR_BRIGHTNESS],
                projection.brightness_range if projection is not None else None,
            )

        # 设置色温：只在实体投影明确支持 COLOR_TEMP 时下发 ct。
        if (
            ATTR_COLOR_TEMP_KELVIN in kwargs
            and projection is not None
            and ColorMode.COLOR_TEMP in projection.supported_color_modes
        ):
            kelvin = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
            params[projection.color_temp_key] = self._clamp_color_temp_kelvin(
                kelvin,
                projection.color_temp_range_kelvin,
            )

        # 设置 RGB 颜色
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            color = (r << 16) | (g << 8) | b
            params[projection.rgb_key if projection is not None else "c"] = color

        try:
            await self.coordinator.async_control_device(self._device_id, params)
        except YeelightProError as err:
            raise_service_error("light.turn_on", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭灯光。"""
        projection = self._projection
        power_key = projection.power_key if projection is not None else "p"
        try:
            await self.coordinator.async_control_device(
                self._device_id, {power_key: False}
            )
        except YeelightProError as err:
            raise_service_error("light.turn_off", err)

    def _brightness_from_ha(
        self, brightness: int, brightness_range: NumericRange | None
    ) -> int:
        """将 HA 亮度转换为源设备亮度。"""
        minimum = brightness_range.min if brightness_range and brightness_range.min is not None else 1
        maximum = brightness_range.max if brightness_range and brightness_range.max is not None else 100
        if maximum <= minimum:
            return max(0, min(255, int(brightness)))

        normalized = max(0.0, min(1.0, brightness / 255))
        return int(round(minimum + normalized * (maximum - minimum)))

    def _clamp_color_temp_kelvin(
        self, kelvin: int, color_temp_range: NumericRange | None
    ) -> int:
        """将色温钳制到支持的开尔文范围内。"""
        minimum = (
            color_temp_range.min
            if color_temp_range and color_temp_range.min is not None
            else 2700
        )
        maximum = (
            color_temp_range.max
            if color_temp_range and color_temp_range.max is not None
            else 6500
        )
        return max(minimum, min(maximum, kelvin))
