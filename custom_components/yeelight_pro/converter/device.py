"""构建规范运行时设备实例的辅助工具。"""

from __future__ import annotations

from typing import Any, Mapping

from ..adapters.device import YeelightLanDeviceAdapter
from ..adapters.models import (
    SourceDeviceComponentInput,
    SourceDeviceInfoInput,
    SourceDeviceInstanceInput,
)
from ..canonical.models import (
    ComponentInstanceModel,
    DeviceInfoModel,
    HADeviceInstanceModel,
)


class CanonicalDeviceInstanceBuilder:
    """从标准化映射构建规范设备实例。"""

    def build(
        self, payload: Mapping[str, Any] | SourceDeviceInstanceInput
    ) -> HADeviceInstanceModel:
        """从标准化载荷构建规范设备实例。"""
        if isinstance(payload, SourceDeviceInstanceInput):
            return HADeviceInstanceModel(
                device_id=payload.device_id,
                name=payload.name,
                online=payload.online,
                product_ref={"model_id": payload.model_id} if payload.model_id else {},
                device_info=self._build_device_info(payload.device_info),
                components=[
                    self._build_component(component) for component in payload.components
                ],
                extensions=dict(payload.extensions),
            )
        return HADeviceInstanceModel.from_dict(payload)

    def _build_device_info(
        self, payload: SourceDeviceInfoInput | None
    ) -> DeviceInfoModel | None:
        """构建设备信息模型。"""
        if payload is None:
            return None
        return DeviceInfoModel(
            identifiers=[list(item) for item in payload.identifiers],
            connections=[list(item) for item in payload.connections],
            via_device=list(payload.via_device) if payload.via_device else None,
            manufacturer=payload.manufacturer,
            model=payload.model,
            model_id=payload.model_id,
            name=payload.name,
            serial_number=payload.serial_number,
            sw_version=payload.sw_version,
            hw_version=payload.hw_version,
            configuration_url=payload.configuration_url,
            entry_type=payload.entry_type,
            suggested_area=payload.suggested_area,
            default_manufacturer=payload.default_manufacturer,
            default_model=payload.default_model,
            default_name=payload.default_name,
            translation_key=payload.translation_key,
            translation_placeholders=payload.translation_placeholders,
        )

    def _build_component(
        self, payload: SourceDeviceComponentInput
    ) -> ComponentInstanceModel:
        """构建组件实例模型。"""
        return ComponentInstanceModel.from_dict(
            {
                "component_id": payload.component_key,
                "name": payload.name,
                "desc": payload.desc,
                "index": payload.index,
                "component_type": payload.component_type,
                "category": payload.category,
                "available": payload.available,
                "instance_capabilities": (
                    {
                        "features": list(payload.instance_capabilities.features),
                        "constraints": dict(payload.instance_capabilities.constraints),
                    }
                    if payload.instance_capabilities is not None
                    else None
                ),
                "state": dict(payload.state),
            }
        )


class YeelightLanDeviceInstanceConverter:
    """Yeelight LAN 运行时载荷的适配器 + 构建器门面。"""

    def __init__(
        self,
        *,
        adapter: YeelightLanDeviceAdapter | None = None,
        builder: CanonicalDeviceInstanceBuilder | None = None,
    ) -> None:
        self._adapter = adapter or YeelightLanDeviceAdapter()
        self._builder = builder or CanonicalDeviceInstanceBuilder()

    def convert(
        self,
        payload: Mapping[str, Any],
        *,
        product_model: Any | None = None,
        model_id: str | None = None,
        device_info: Mapping[str, Any] | None = None,
    ) -> HADeviceInstanceModel:
        """将运行时载荷转换为规范设备实例。"""
        normalized = self._adapter.adapt(
            payload,
            product_model=product_model,
            model_id=model_id,
            device_info=device_info,
        )
        return self._builder.build(normalized)
