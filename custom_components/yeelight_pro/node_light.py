"""Yeelight Pro topology-node light entities."""

from __future__ import annotations

from typing import Any, Dict, Mapping

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
from .identity import coordinator_identity_scope
from .light_group import (
    _color_mode_from_params,
    _rgb_color_from_params,
    _supported_color_modes_from_params,
)
from .node_metadata import (
    node_kind_icon,
    node_kind_label,
    node_light_unique_id,
    topology_node_id,
    topology_node_name,
    topology_node_params,
)
from .utils import to_bool
from .projector.light_helpers import (
    DEFAULT_MAX_COLOR_TEMP_KELVIN,
    DEFAULT_MIN_COLOR_TEMP_KELVIN,
)

try:
    from homeassistant.components.light import ATTR_COLOR_TEMP_KELVIN
except ImportError:  # pragma: no cover - 兼容旧版 HA
    from homeassistant.components.light import ATTR_COLOR_TEMP as ATTR_COLOR_TEMP_KELVIN


class YeelightProNodeLight(CoordinatorEntity, LightEntity):
    """Yeelight Pro 房间/区域/整屋总控灯光实体。"""

    _attr_has_entity_name = True
    _attr_min_color_temp_kelvin = DEFAULT_MIN_COLOR_TEMP_KELVIN
    _attr_max_color_temp_kelvin = DEFAULT_MAX_COLOR_TEMP_KELVIN

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        node_kind: str,
        node_id: str,
    ) -> None:
        """初始化拓扑节点灯光实体。"""
        super().__init__(coordinator)
        self._node_kind = node_kind
        self._node_id = node_id
        self._attr_unique_id = node_light_unique_id(
            coordinator_identity_scope(coordinator),
            node_kind,
            node_id,
        )
        self._attr_icon = node_kind_icon(node_kind)

    @property
    def _node(self) -> Mapping[str, Any] | None:
        """返回当前节点缓存。"""
        for row in _node_rows(self.coordinator, self._node_kind):
            if topology_node_id(row, self._node_kind) == self._node_id:
                return row
        return None

    @property
    def name(self) -> str | None:
        """返回节点名称。"""
        node = self._node
        if node is None:
            return None
        return topology_node_name(node, self._node_kind, self._node_id)

    @property
    def device_info(self) -> Dict[str, Any]:
        """返回关联的家庭设备信息。"""
        return house_device_info(
            self.coordinator,
            name_suffix=f"{node_kind_label(self._node_kind)}总控",
        )

    @property
    def suggested_object_id(self) -> str | None:
        """返回 HA 首次注册时使用的友好实体 ID 建议。"""
        return suggested_entity_object_id(
            self.device_info,
            entity_name=self.name,
            fallback_id=f"{self._node_kind}_{self._node_id}",
        )

    @property
    def available(self) -> bool:
        """返回节点是否可用。"""
        node = self._node
        if node is None:
            return False
        return to_bool(node.get("online"), default=True)

    @property
    def is_on(self) -> bool:
        """返回节点总控是否开启。"""
        return to_bool(self._node_params.get("p"), default=False)

    @property
    def brightness(self) -> int | None:
        """返回节点总控亮度（0..255）。"""
        value = self._node_params.get("l")
        if not isinstance(value, int | float):
            return None
        return int(round(max(0, min(100, value)) * 255 / 100))

    @property
    def color_temp_kelvin(self) -> int | None:
        """返回节点总控色温。"""
        value = self._node_params.get("ct")
        return int(value) if isinstance(value, int | float) and value > 0 else None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """返回节点总控 RGB 颜色。"""
        return _rgb_color_from_params(self._node_params)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """返回 HA 允许的节点总控颜色模式集合。"""
        return _supported_color_modes_from_params(self._node_params)

    @property
    def color_mode(self) -> ColorMode:
        """返回当前节点总控颜色模式。"""
        return _color_mode_from_params(self._node_params)

    @property
    def _node_params(self) -> dict[str, Any]:
        """返回节点 params/properties，缺失时给出空字典。"""
        node = self._node
        return topology_node_params(node) if node is not None else {}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """开启节点总控。"""
        params: dict[str, Any] = {"p": True}
        if ATTR_BRIGHTNESS in kwargs:
            brightness = max(0, min(255, kwargs[ATTR_BRIGHTNESS]))
            params["l"] = int(round(brightness * 100 / 255))
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            params["ct"] = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
        if ATTR_RGB_COLOR in kwargs and "c" in self._node_params:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            params["c"] = (r << 16) | (g << 8) | b
        try:
            await self.coordinator.async_control_node(
                self._node_kind,
                self._node_id,
                params,
            )
        except YeelightProError as err:
            raise_service_error("light.turn_on", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭节点总控。"""
        try:
            await self.coordinator.async_control_node(
                self._node_kind,
                self._node_id,
                {"p": False},
            )
        except YeelightProError as err:
            raise_service_error("light.turn_off", err)


def _node_rows(coordinator: YeelightProCoordinator, node_kind: str) -> list[Mapping[str, Any]]:
    """返回指定类型的拓扑节点列表。"""
    rows = getattr(coordinator, f"{node_kind}s", None)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


__all__ = ["YeelightProNodeLight"]
