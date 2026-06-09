"""Yeelight IoT 能力注册表模型."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class IoTCategorySpec:
    """Yeelight IoT 品类定义."""

    category: str
    category_id: int
    name: str
    platform: str | None
    description: str


@dataclass(frozen=True, slots=True)
class IoTComponentSpec:
    """Yeelight IoT 组件定义."""

    component_id: int
    alias: str
    name: str
    category: str | None
    component_type: str
    platform_hint: str | None = None
    properties: tuple[str, ...] = ()
    events: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PropertyCapability:
    """一个属性在 Home Assistant 中的含义."""

    prop: str
    device_class: str | None = None
    unit: str | None = None
    control_key: str | None = None


@dataclass(frozen=True, slots=True)
class IoTPropertySpec:
    """Yeelight IoT 属性定义."""

    prop: str
    full_name: str
    data_type: str
    access: str
    category: str
    handler: str
    capability: PropertyCapability | None = None
    components: tuple[str, ...] = ()
    unit: str | None = None
    value_range: tuple[int | float | None, int | float | None, int | float | None] | None = None
    value_list: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        """冻结枚举值映射，避免运行期被意外修改."""
        object.__setattr__(self, "value_list", MappingProxyType(dict(self.value_list)))

    @property
    def readable(self) -> bool:
        """属性是否可读."""
        return "read" in self.access.lower()

    @property
    def writable(self) -> bool:
        """属性是否可写."""
        return "write" in self.access.lower()


@dataclass(frozen=True, slots=True)
class IoTEventSpec:
    """Yeelight IoT 事件定义."""

    event_type: str
    normalized: str
    event_id: int | None = None
    description: str | None = None
    aliases: tuple[str, ...] = ()
    components: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IoTProtocolSpec:
    """Yeelight IoT 连接协议定义."""

    protocol_id: int
    key: str
    name: str
    description: str
    bridge_protocol: bool = False


@dataclass(frozen=True, slots=True)
class ControlKey:
    """组件属性控制 key 解析结果."""

    component_index: int | None
    prop_name: str
