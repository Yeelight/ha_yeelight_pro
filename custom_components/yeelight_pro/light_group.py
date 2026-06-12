"""Yeelight Pro group light entity."""

from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .device_display import suggested_entity_object_id
from .entity_errors import raise_service_error
from .house_metadata import house_device_info

try:
    from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN
except ImportError:  # pragma: no cover - 兼容旧版 HA
    from homeassistant.components.light import ATTR_COLOR_TEMP as ATTR_COLOR_TEMP_KELVIN


class YeelightProGroupLight(CoordinatorEntity, LightEntity):
    """Yeelight Pro 灯组灯光实体。"""

    _attr_has_entity_name = True
    _attr_icon = "mdi:lightbulb-group"
    _attr_min_color_temp_kelvin = 2700
    _attr_max_color_temp_kelvin = 6500

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        group_id: str,
    ) -> None:
        """初始化灯组灯光实体。"""
        super().__init__(coordinator)
        self._group_id = group_id
        self._attr_unique_id = f"{DOMAIN}_group_{self._group_id}_light"

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
    def supported_color_modes(self) -> set[ColorMode]:
        """返回 HA 允许的灯组颜色模式集合。"""
        if self.color_temp_kelvin is not None:
            return {ColorMode.COLOR_TEMP}
        return {ColorMode.BRIGHTNESS}

    @property
    def color_mode(self) -> ColorMode:
        """返回当前灯组颜色模式。"""
        if self.color_temp_kelvin is not None:
            return ColorMode.COLOR_TEMP
        return ColorMode.BRIGHTNESS

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
        try:
            await self.coordinator.async_control_group(self._group_id, params)
        except YeelightProError as err:
            raise_service_error("light.turn_on", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭灯组。"""
        try:
            await self.coordinator.async_control_group(self._group_id, {"p": False})
        except YeelightProError as err:
            raise_service_error("light.turn_off", err)


__all__ = ["YeelightProGroupLight"]
