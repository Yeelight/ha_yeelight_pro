"""Yeelight Pro Open API property control and read operations."""

from __future__ import annotations

from typing import Any

from .client_helpers import (
    control_nodes_property_body,
    control_properties_body,
    control_property_body,
    read_nodes_properties_body,
    read_nodes_property_body,
    read_properties_body,
)
from .client_node_base import YeelightProNodeRequestMixin
from .client_paths import (
    automation_action_path,
    node_properties_control_path,
    node_properties_read_path,
    node_property_control_path,
    node_property_read_path,
    nodes_property_control_path,
    nodes_properties_read_path,
    nodes_property_read_path,
    scene_execute_path,
)


class YeelightProNodePropertyMixin(YeelightProNodeRequestMixin):
    """开放平台节点属性控制、读取、场景和自动化动作接口."""

    async def control_device(
        self,
        house_id: int,
        device_id: int,
        params: dict[str, Any],
        duration: int = 500,
    ) -> bool:
        """控制设备."""
        await self._control_node_properties(
            house_id=house_id,
            node_kind="device",
            resource_id=device_id,
            command="set",
            params=params,
            duration=duration,
        )
        return True

    async def toggle_device(
        self,
        house_id: int,
        device_id: int,
        properties: list[str],
        duration: int = 500,
    ) -> bool:
        """切换设备属性."""
        await self._control_node_properties(
            house_id=house_id,
            node_kind="device",
            resource_id=device_id,
            command="toggle",
            properties=properties,
            duration=duration,
        )
        return True

    async def execute_scene(self, house_id: int, scene_id: str) -> bool:
        """执行场景."""
        await self._request("POST", scene_execute_path(house_id, scene_id))
        return True

    async def control_group(
        self,
        house_id: int,
        group_id: str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> bool:
        """控制灯组属性."""
        await self._control_node_properties(
            house_id=house_id,
            node_kind="group",
            resource_id=group_id,
            command="set",
            params=params,
            duration=duration,
        )
        return True

    async def control_node_property(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_id: int | str,
        property_name: str,
        command: str,
        value: Any | None = None,
        duration: int | None = None,
        delay: int | None = None,
        index: int | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """控制单个开放平台节点的单个属性."""
        return await self._request(
            "POST",
            node_property_control_path(
                house_id=house_id,
                node_kind=node_kind,
                resource_id=resource_id,
                property_name=property_name,
            ),
            json=control_property_body(
                command=command,
                value=value,
                duration=duration,
                delay=delay,
                index=index,
                category=category,
            ),
        )

    async def control_node_properties(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_id: int | str,
        command: str,
        params: dict[str, Any] | None = None,
        properties: list[str] | None = None,
        duration: int | None = None,
        delay: int | None = None,
        index: int | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """控制单个开放平台节点的多个属性."""
        return await self._request(
            "POST",
            node_properties_control_path(
                house_id=house_id,
                node_kind=node_kind,
                resource_id=resource_id,
            ),
            json=control_properties_body(
                command=command,
                params=params,
                properties=properties,
                duration=duration,
                delay=delay,
                index=index,
                category=category,
            ),
        )

    async def control_nodes_property(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_ids: list[int | str],
        property_name: str,
        command: str,
        value: Any | None = None,
        duration: int | None = None,
        delay: int | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """控制多个开放平台节点的单个属性."""
        return await self._request(
            "POST",
            nodes_property_control_path(
                house_id=house_id,
                node_kind=node_kind,
                property_name=property_name,
            ),
            json=control_nodes_property_body(
                resource_ids=resource_ids,
                command=command,
                value=value,
                duration=duration,
                delay=delay,
                category=category,
            ),
        )

    async def read_node_properties(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_id: int | str,
        properties: list[str],
        index: int | None = None,
    ) -> dict[str, Any]:
        """读取单个开放平台节点的多个属性值."""
        return await self._request(
            "POST",
            node_properties_read_path(
                house_id=house_id,
                node_kind=node_kind,
                resource_id=resource_id,
            ),
            json=read_properties_body(properties, index=index),
        )

    async def read_node_property(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_id: int | str,
        property_name: str,
        index: int | None = None,
    ) -> dict[str, Any]:
        """读取单个开放平台节点的单个属性值."""
        return await self._request(
            "POST",
            node_property_read_path(
                house_id=house_id,
                node_kind=node_kind,
                resource_id=resource_id,
                property_name=property_name,
            ),
            json=({} if index is None else {"index": index}),
        )

    async def read_nodes_property(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_ids: list[int | str],
        property_name: str,
    ) -> dict[str, Any]:
        """读取多个开放平台节点的单个属性值."""
        return await self._request(
            "POST",
            nodes_property_read_path(
                house_id=house_id,
                node_kind=node_kind,
                property_name=property_name,
            ),
            json=read_nodes_property_body(resource_ids),
        )

    async def read_nodes_properties(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_ids: list[int | str],
        properties: list[str],
    ) -> dict[str, Any]:
        """读取多个开放平台节点的多个属性值."""
        return await self._request(
            "POST",
            nodes_properties_read_path(house_id=house_id, node_kind=node_kind),
            json=read_nodes_properties_body(resource_ids, properties),
        )

    async def _control_node_properties(
        self,
        *,
        house_id: int,
        node_kind: str,
        resource_id: int | str,
        command: str,
        duration: int,
        params: dict[str, Any] | None = None,
        properties: list[str] | None = None,
    ) -> None:
        """按开放平台 nodeType 统一下发节点属性控制."""
        await self.control_node_properties(
            house_id=house_id,
            node_kind=node_kind,
            resource_id=resource_id,
            command=command,
            params=params,
            properties=properties,
            duration=duration,
        )

    async def enable_automation(self, automation_id: str) -> bool:
        """启用自动化."""
        await self._request("POST", automation_action_path(automation_id, "enable"))
        return True

    async def disable_automation(self, automation_id: str) -> bool:
        """禁用自动化."""
        await self._request("POST", automation_action_path(automation_id, "disable"))
        return True

    async def trigger_automation(self, automation_id: str) -> bool:
        """手动触发自动化."""
        await self._request("POST", automation_action_path(automation_id, "trigger"))
        return True
