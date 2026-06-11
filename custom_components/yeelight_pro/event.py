"""Yeelight Pro event 平台.

将 canonical 事件型组件（情景面板、旋钮、按钮等）投影为 Home Assistant event 实体，
并监听集成内部运行时事件总线完成触发回调。
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    DEVICE_EVENT_TYPE,
    DOMAIN,
)
from .core.coordinator import YeelightProCoordinator
from .dynamic_entities import async_track_dynamic_entities
from .projector.event import HAEventProjection, project_events

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro event 平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_event_entities,
        logger=_LOGGER,
        platform_name="event",
    )


def _iter_event_entities(coordinator: YeelightProCoordinator) -> list["YeelightProEventEntity"]:
    """按当前拓扑生成 event 实体候选."""
    entities: list[YeelightProEventEntity] = []
    for device_id, device_data in coordinator.data.items():
        for projection in project_events(device_data, domain=DOMAIN):
            entities.append(
                YeelightProEventEntity(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )
    return entities


class YeelightProEventEntity(CoordinatorEntity, EventEntity):
    """Yeelight Pro event 实体."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        source_device_id: int,
        *,
        component_id: str,
    ) -> None:
        """初始化 event 实体."""
        super().__init__(coordinator)
        self._source_device_id = source_device_id
        self._component_id = component_id

        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{source_device_id}_{component_id}_event"
        )
        self._fallback_event_types: list[str] = []
        if projection is not None:
            self._fallback_event_types = list(projection.event_types)
            self._attr_device_class = projection.device_class

    @property
    def _projection(self) -> HAEventProjection | None:
        """返回最新的 event 投影视图."""
        projections = project_events(
            self.coordinator.get_device(self._source_device_id),
            domain=DOMAIN,
        )
        return next(
            (item for item in projections if item.component_id == self._component_id),
            None,
        )

    @property
    def name(self) -> str | None:
        """返回实体名称."""
        projection = self._projection
        return projection.name if projection is not None else None

    @property
    def available(self) -> bool:
        """返回实体是否可用."""
        projection = self._projection
        if projection is None:
            return False
        return projection.available

    @property
    def event_types(self) -> list[str]:
        """返回当前 schema 投影声明的事件类型."""
        projection = self._projection
        if projection is not None:
            self._fallback_event_types = list(projection.event_types)
            return list(projection.event_types)
        return list(self._fallback_event_types)

    @property
    def device_info(self) -> dict[str, Any] | None:
        """返回 Home Assistant 设备信息."""
        projection = self._projection
        if projection is None:
            return None
        return projection.device_info

    @property
    def icon(self) -> str | None:
        """返回实体图标."""
        projection = self._projection
        if projection is None:
            return None
        return projection.icon

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回稳定的调试属性."""
        return {
            "component_id": self._component_id,
            "source_device_id": str(self._source_device_id),
        }

    async def async_added_to_hass(self) -> None:
        """注册运行时事件监听."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.hass.bus.async_listen(DEVICE_EVENT_TYPE, self._handle_runtime_event)
        )

    @callback
    def _handle_runtime_event(self, event: Event) -> None:
        """处理集成内部运行时事件."""
        payload = event.data
        if str(payload.get(ATTR_SOURCE_DEVICE_ID)) != str(self._source_device_id):
            return
        if str(payload.get(ATTR_COMPONENT_ID)) != self._component_id:
            return

        event_type = payload.get(ATTR_EVENT_TYPE)
        if not isinstance(event_type, str):
            return
        if event_type not in self.event_types:
            _LOGGER.debug(
                "Ignoring unsupported event_type=%s for %s/%s",
                event_type,
                self._source_device_id,
                self._component_id,
            )
            return

        attributes = payload.get(ATTR_EVENT_ATTRIBUTES)
        self._trigger_event(
            event_type,
            dict(attributes) if isinstance(attributes, dict) else None,
        )
        self.async_write_ha_state()
