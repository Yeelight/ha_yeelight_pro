"""适配器层标准化源侧模型，供转换器消费。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceValueRangeInput:
    """适配器层源侧数值范围元数据。"""

    min: int | None = None
    max: int | None = None
    step: int | None = None


@dataclass(slots=True)
class SourceValueItemInput:
    """适配器层源侧枚举值元数据。"""

    code: str
    desc: str | None = None


@dataclass(slots=True)
class SourcePropertyInput:
    """适配器层标准化源侧属性定义。"""

    property_key: str
    name: str | None = None
    desc: str | None = None
    semantic: str | None = None
    kind: str | None = None
    property_type: str | None = None
    format: str | None = None
    unit: str | None = None
    access: str | None = None
    default: Any = None
    value_range: SourceValueRangeInput | None = None
    value_list: list[SourceValueItemInput] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceEventInput:
    """适配器层标准化源侧事件定义。"""

    event_key: str
    name: str | None = None
    desc: str | None = None
    semantic: str | None = None
    params: list[SourcePropertyInput] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceActionParamInput:
    """适配器层标准化源侧动作参数定义。"""

    param_key: str
    name: str | None = None
    desc: str | None = None
    format: str | None = None
    unit: str | None = None
    default: Any = None
    value_range: SourceValueRangeInput | None = None
    value_list: list[SourceValueItemInput] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceActionInput:
    """适配器层标准化源侧动作定义。"""

    action_key: str
    name: str | None = None
    desc: str | None = None
    semantic: str | None = None
    scope: str = "component"
    targets: list[str] = field(default_factory=list)
    params: list[SourceActionParamInput] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceBridgeInput:
    """适配器层标准化源侧桥接元数据。"""

    protocols: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceComponentInput:
    """适配器层标准化源侧组件定义。"""

    component_key: str
    name: str | None = None
    desc: str | None = None
    component_type: str | None = None
    category: str | None = None
    capabilities: list[str] = field(default_factory=list)
    properties: list[SourcePropertyInput] = field(default_factory=list)
    events: list[SourceEventInput] = field(default_factory=list)
    actions: list[SourceActionInput] = field(default_factory=list)
    cid: int | None = None
    index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceProductSchemaInput:
    """适配器层标准化源侧产品模型输入。"""

    source: str
    product_key: str
    model_id: str | None = None
    manufacturer: str | None = None
    name: str | None = None
    description: str | None = None
    category: str | None = None
    categories: list[str] = field(default_factory=list)
    bridge: SourceBridgeInput | None = None
    components: list[SourceComponentInput] = field(default_factory=list)
    device_actions: list[SourceActionInput] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceInstanceCapabilitiesInput:
    """适配器层标准化源侧实例能力增量。"""

    features: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceDeviceInfoInput:
    """适配器层标准化源侧 HA 设备注册表投影。"""

    identifiers: list[list[str]] = field(default_factory=list)
    connections: list[list[str]] = field(default_factory=list)
    via_device: list[str] | None = None
    manufacturer: str | None = None
    model: str | None = None
    model_id: str | None = None
    name: str | None = None
    serial_number: str | None = None
    sw_version: str | None = None
    hw_version: str | None = None
    configuration_url: str | None = None
    entry_type: str | None = None
    suggested_area: str | None = None
    default_manufacturer: str | None = None
    default_model: str | None = None
    default_name: str | None = None
    translation_key: str | None = None
    translation_placeholders: dict[str, Any] | None = None


@dataclass(slots=True)
class SourceDeviceComponentInput:
    """适配器层标准化源侧设备组件运行时载荷。"""

    component_key: str
    name: str | None = None
    desc: str | None = None
    index: int | None = None
    component_type: str | None = None
    category: str | None = None
    available: bool = True
    state: dict[str, Any] = field(default_factory=dict)
    instance_capabilities: SourceInstanceCapabilitiesInput | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceDeviceInstanceInput:
    """适配器层标准化源侧设备实例输入。"""

    source: str
    device_id: str
    product_key: str | None = None
    model_id: str | None = None
    name: str | None = None
    online: bool = True
    device_info: SourceDeviceInfoInput | None = None
    components: list[SourceDeviceComponentInput] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
