"""Yeelight Pro group light entity."""

from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .device_display import suggested_entity_object_id
from .entity_errors import raise_service_error
from .house_metadata import house_device_info
from .identity import entity_unique_id
from .light_control_helpers import transition_duration_ms
from .projector.light_helpers import (
    DEFAULT_MAX_COLOR_TEMP_KELVIN,
    DEFAULT_MIN_COLOR_TEMP_KELVIN,
)
from .utils import to_int

try:
    from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN
except ImportError:  # pragma: no cover - 兼容旧版 HA
    from homeassistant.components.light import ATTR_COLOR_TEMP as ATTR_COLOR_TEMP_KELVIN


class YeelightProGroupLight(CoordinatorEntity, LightEntity):
    """Yeelight Pro 灯组灯光实体。"""

    _attr_has_entity_name = True
    _attr_icon = "mdi:lightbulb-group"
    _attr_min_color_temp_kelvin = DEFAULT_MIN_COLOR_TEMP_KELVIN
    _attr_max_color_temp_kelvin = DEFAULT_MAX_COLOR_TEMP_KELVIN

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        group_id: str,
    ) -> None:
        """初始化灯组灯光实体。"""
        super().__init__(coordinator)
        self._group_id = group_id
        self._attr_unique_id = entity_unique_id(
            coordinator,
            "group",
            self._group_id,
            "light",
        )

    @property
    def _group(self) -> dict[str, Any] | None:
        """返回当前灯组缓存。"""
        for group in self.coordinator.groups:
            if str(group.get("id") or group.get("groupId")) == self._group_id:
                return group
        return None

    @property
    def name(self) -> str | None:
        """返回灯组名称。"""
        group = self._group
        if group is None:
            return None
        return str(group.get("name") or group.get("groupName") or f"灯组 {self._group_id}")

    @property
    def device_info(self) -> Dict[str, Any]:
        """返回关联的家庭设备信息。"""
        return house_device_info(self.coordinator, name_suffix="灯组")

    @property
    def available(self) -> bool:
        """返回灯组是否可用。"""
        group = self._group
        if group is None:
            return False
        return bool(group.get("online", True))

    @property
    def is_on(self) -> bool:
        """返回灯组是否开启。"""
        return bool(self._group_params.get("p", False))

    @property
    def brightness(self) -> int | None:
        """返回灯组亮度（0..255）。"""
        value = self._group_params.get("l")
        if not isinstance(value, int | float):
            return None
        return int(round(max(0, min(100, value)) * 255 / 100))

    @property
    def color_temp_kelvin(self) -> int | None:
        """返回灯组色温。"""
        value = self._group_params.get("ct")
        return int(value) if isinstance(value, int | float) and value > 0 else None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """返回灯组 RGB 颜色。"""
        return _rgb_color_from_params(self._group_params)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """返回 HA 允许的灯组颜色模式集合。"""
        return _supported_color_modes_from_params(self._group_params)

    @property
    def color_mode(self) -> ColorMode:
        """返回当前灯组颜色模式。"""
        return _color_mode_from_params(self._group_params)

    @property
    def suggested_object_id(self) -> str | None:
        """返回 HA 首次注册时使用的友好实体 ID 建议。"""
        return suggested_entity_object_id(
            self.device_info,
            entity_name=self.name,
            fallback_id=f"group_{self._group_id}",
        )

    @property
    def _group_params(self) -> dict[str, Any]:
        """返回灯组 params，缺失时给出空字典。"""
        group = self._group
        params = group.get("params") if group is not None else None
        return dict(params) if isinstance(params, dict) else {}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """开启灯组。"""
        params: dict[str, Any] = {"p": True}
        if ATTR_BRIGHTNESS in kwargs:
            brightness = max(0, min(255, kwargs[ATTR_BRIGHTNESS]))
            params["l"] = int(round(brightness * 100 / 255))
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            params["ct"] = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
        if ATTR_RGB_COLOR in kwargs and "c" in self._group_params:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            params["c"] = (r << 16) | (g << 8) | b
        try:
            duration = transition_duration_ms(kwargs)
            if duration is None:
                await self.coordinator.async_control_group(self._group_id, params)
            else:
                await self.coordinator.async_control_group(
                    self._group_id,
                    params,
                    duration=duration,
                )
        except YeelightProError as err:
            raise_service_error("light.turn_on", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭灯组。"""
        try:
            duration = transition_duration_ms(kwargs)
            if duration is None:
                await self.coordinator.async_control_group(self._group_id, {"p": False})
            else:
                await self.coordinator.async_control_group(
                    self._group_id,
                    {"p": False},
                    duration=duration,
                )
        except YeelightProError as err:
            raise_service_error("light.turn_off", err)


def _supported_color_modes_from_params(params: dict[str, Any]) -> set[ColorMode]:
    """根据灯组/节点当前参数证据推断 HA 颜色模式。"""
    modes: set[ColorMode] = set()
    if "ct" in params:
        modes.add(ColorMode.COLOR_TEMP)
    if "c" in params:
        modes.add(ColorMode.RGB)
    if modes:
        return modes
    if "l" in params:
        return {ColorMode.BRIGHTNESS}
    return {ColorMode.ONOFF}


def _color_mode_from_params(params: dict[str, Any]) -> ColorMode:
    """解析当前灯光模式，优先使用易来 m 模式字段。"""
    supported = _supported_color_modes_from_params(params)
    mode = to_int(params.get("m"))
    if mode == 1 and ColorMode.RGB in supported:
        return ColorMode.RGB
    if mode == 2 and ColorMode.COLOR_TEMP in supported:
        return ColorMode.COLOR_TEMP
    if _color_temp_from_params(params) is not None and ColorMode.COLOR_TEMP in supported:
        return ColorMode.COLOR_TEMP
    if _rgb_color_from_params(params) is not None and ColorMode.RGB in supported:
        return ColorMode.RGB
    if ColorMode.BRIGHTNESS in supported:
        return ColorMode.BRIGHTNESS
    return ColorMode.ONOFF


def _color_temp_from_params(params: dict[str, Any]) -> int | None:
    """读取 params 中的开尔文色温。"""
    value = params.get("ct")
    return int(value) if isinstance(value, int | float) and value > 0 else None


def _rgb_color_from_params(params: dict[str, Any]) -> tuple[int, int, int] | None:
    """读取 params 中的 RGB 整数色彩。"""
    color = to_int(params.get("c"))
    if color is None:
        return None
    return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)


__all__ = ["YeelightProGroupLight"]
