"""Yeelight Pro 设备实体基类."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..identity import (
    coordinator_identity_scope,
    device_entity_unique_id,
    scoped_device_identifier,
)
from ..core.coordinator import YeelightProCoordinator


class YeelightProEntity(CoordinatorEntity[YeelightProCoordinator], Entity):
    """Yeelight Pro 设备实体基类."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int,
        component_id: str,
    ):
        """初始化实体."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        self._attr_unique_id = device_entity_unique_id(
            coordinator,
            device_id,
            component_id,
        )

    @property
    def device_data(self) -> dict[str, Any] | None:
        """返回设备数据."""
        return self.coordinator.get_device(self._device_id)

    @property
    def device_info(self) -> dict[str, Any]:
        """返回设备信息."""
        data = self.device_data
        if not data:
            return {}

        return {
            "identifiers": {
                (
                    DOMAIN,
                    scoped_device_identifier(
                        coordinator_identity_scope(self.coordinator),
                        self._device_id,
                    ),
                )
            },
            "name": data.get("name", f"Device {self._device_id}"),
            "manufacturer": "Yeelight",
            "model": data.get("product_schema", {}).get("name", "Unknown"),
            "sw_version": data.get("sw_version"),
        }

    @property
    def available(self) -> bool:
        """返回设备是否可用."""
        data = self.device_data
        if not data:
            return False
        return data.get("online", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回额外的状态属性."""
        data = self.device_data
        if not data:
            return {}

        return {
            "device_id": self._device_id,
            "gateway_id": data.get("gatewayDeviceId"),
            "product_id": data.get("pid"),
        }
