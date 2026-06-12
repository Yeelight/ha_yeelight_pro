"""Yeelight IoT 能力注册表查询 API."""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Any, Mapping

from ..utils import to_category, to_int, to_str
from .data import (
    IOT_CATEGORY_SPECS,
    IOT_COMPONENT_SPECS,
    IOT_EVENT_SPECS,
    IOT_PROPERTY_SPECS,
    IOT_PROTOCOL_SPECS,
    NODE_TYPE_MAP,
)
from .models import (
    ControlKey,
    IoTCategorySpec,
    IoTComponentSpec,
    IoTEventSpec,
    IoTPropertySpec,
    IoTProductSpec,
    IoTProtocolSpec,
    PropertyCapability,
)
from .property_index import enrich_property_component_memberships
from .property_aliases import PROPERTY_ALIASES
from .product_catalog import (
    is_projectable_global_component as _is_projectable_global_component,
    normalize_product_pid as _normalize_product_pid,
    product_catalog,
    product_category_candidates as _product_category_candidates,
    product_components as _product_components,
    product_hydration_properties as _product_hydration_properties,
    product_model_from_catalog as _product_model_from_catalog,
    product_projectable_global_components as _product_projectable_global_components,
    product_protocols as _product_protocols,
    product_spec as _product_spec,
    registry_property_model,
)

_KEY_RE = re.compile(r"^(?P<index>\d+)-(?P<prop>.+)$")
_NON_ALNUM_RE = re.compile(r"[^\w]+")
_PLATFORM_NON_CATEGORIES = frozenset({"event", "scene", "button", "select", "number", "vacuum", "text"})
class YeelightIoTRegistry:
    """内置 Yeelight IoT 物模型能力注册表."""

    def __init__(
        self,
        *,
        categories: tuple[IoTCategorySpec, ...] = IOT_CATEGORY_SPECS,
        components: tuple[IoTComponentSpec, ...] = IOT_COMPONENT_SPECS,
        properties: tuple[IoTPropertySpec, ...] = IOT_PROPERTY_SPECS,
        events: tuple[IoTEventSpec, ...] = IOT_EVENT_SPECS,
        protocols: tuple[IoTProtocolSpec, ...] = IOT_PROTOCOL_SPECS,
    ) -> None:
        """构建只读索引."""
        self.categories = categories
        self.components = components
        self.properties = enrich_property_component_memberships(properties, components)
        self.events = events
        self.protocols = protocols
        self.product_catalog = product_catalog()

        self.category_map = {item.category: item for item in categories}
        self.category_platform_map = {
            item.category: item.platform for item in categories if item.platform is not None
        }
        self.component_map = {}
        self.component_platform_hints = {}
        for item in components:
            for key in _component_keys(item):
                self.component_map[key] = item
                if item.platform_hint is not None:
                    self.component_platform_hints[key] = item.platform_hint
        self.property_map = {item.prop: item for item in self.properties}
        self.property_capabilities = {
            item.prop: item.capability
            for item in self.properties
            if item.capability is not None
        }
        self.event_aliases = _build_event_aliases(events)
        self.protocol_key_map = {item.key: item for item in protocols}
        self.protocol_id_map = {item.protocol_id: item for item in protocols}

    def is_iot_category(self, value: Any) -> bool:
        """判断值是否为 Yeelight IoT 品类."""
        category = to_category(value)
        if not category or category in _PLATFORM_NON_CATEGORIES:
            return False
        return category in self.category_map

    def platform_for_category(self, category: Any, *, default: str | None = None) -> str | None:
        """返回 IoT category 对应的 HA 平台名."""
        normalized = to_category(category)
        if not normalized or normalized in _PLATFORM_NON_CATEGORIES:
            return default
        return self.category_platform_map.get(normalized, default)

    def component_platform_hint(self, component: Any, *, default: str | None = None) -> str | None:
        """返回组件的 HA 平台提示."""
        direct = _component_key(component) if not isinstance(component, Mapping) else ""
        if direct and direct in self.component_platform_hints:
            return self.component_platform_hints[direct]

        if isinstance(component, Mapping):
            hint = to_str(component.get("platform_hint") or component.get("platform"))
            if hint:
                return hint
            for key in ("alias", "component_alias", "name", "component_id", "id"):
                value = _component_key(component.get(key))
                if value in self.component_platform_hints:
                    return self.component_platform_hints[value]
            platform = self.platform_for_category(component.get("category"))
            return platform if platform is not None else default

        for attr in ("platform_hint", "platform", "alias", "component_alias", "name", "component_id", "id"):
            attr_value = getattr(component, attr, None)
            if attr in {"platform_hint", "platform"}:
                hint = to_str(attr_value)
                if hint:
                    return hint
            key = _component_key(attr_value)
            if key in self.component_platform_hints:
                return self.component_platform_hints[key]
        platform = self.platform_for_category(getattr(component, "category", None))
        return platform if platform is not None else default

    def property_spec(self, prop: Any) -> IoTPropertySpec | None:
        """返回属性物模型定义."""
        key = normalize_property_key(prop)
        if key is None:
            return None
        return self.property_map.get(key)

    def property_capability(self, prop: Any) -> PropertyCapability | None:
        """返回属性的 HA 能力语义."""
        key = normalize_property_key(prop)
        if key is None:
            return None
        return self.property_capabilities.get(key)

    def normalize_event_type(self, value: Any) -> str | None:
        """将后台事件名/id 归一化为稳定 snake_case 事件类型."""
        text = to_str(value)
        if not text:
            return None
        numeric = to_int(text)
        if numeric is not None and numeric in self.event_aliases:
            return self.event_aliases[numeric]
        normalized = normalize_alias_key(text)
        if not normalized:
            return None
        return self.event_aliases.get(normalized, normalized)

    def protocol(self, value: Any) -> IoTProtocolSpec | None:
        """按协议 key 或 id 查询连接协议."""
        text = to_str(value)
        numeric = to_int(value)
        if numeric is not None and numeric in self.protocol_id_map:
            return self.protocol_id_map[numeric]
        if not text:
            return None
        key = normalize_alias_key(text)
        aliases = {
            "不连接": "none",
            "none": "none",
            "直连": "direct",
            "direct": "direct",
            "mesh协议": "mesh",
            "mesh": "mesh",
            "matter协议": "matter",
            "matter": "matter",
            "dali协议": "dali",
            "dali": "dali",
            "thread协议": "thread",
            "thread": "thread",
        }
        return self.protocol_key_map.get(aliases.get(key, key))

    def node_type(self, value: Any) -> int | None:
        """返回 open platform nodeType 编号."""
        key = to_category(value)
        return NODE_TYPE_MAP.get(key)

    def product_spec(self, pid: Any) -> IoTProductSpec | None:
        """返回 pid 对应的产品构成定义."""
        return _product_spec(pid)

    def product_components(self, pid: Any) -> tuple[IoTComponentSpec, ...]:
        """返回 pid 声明的普通组件定义."""
        return _product_components(pid, self.component_map)

    def product_projectable_global_components(
        self,
        pid: Any,
    ) -> tuple[IoTComponentSpec, ...]:
        """返回 pid 声明且可安全投影的全局组件定义."""
        return _product_projectable_global_components(pid, self.component_map)

    def product_category_candidates(self, pid: Any) -> tuple[str, ...]:
        """返回产品构成声明出的 IoT 品类候选."""
        return _product_category_candidates(pid, self.component_map)

    def product_protocols(self, pid: Any) -> tuple[IoTProtocolSpec, ...]:
        """返回产品构成声明出的连接协议定义."""
        protocols: list[IoTProtocolSpec] = []
        for protocol in _product_protocols(pid):
            spec = self.protocol(protocol)
            if spec is not None:
                protocols.append(spec)
        return tuple(protocols)

    def product_hydration_properties(self, pid: Any) -> tuple[str, ...]:
        """返回产品构成声明出的属性读取集合."""
        return _product_hydration_properties(pid, self.component_map)

    def product_model_from_catalog(self, pid: Any) -> Any | None:
        """从产品构成目录构建 canonical 产品模型."""
        return _product_model_from_catalog(
            pid,
            self.component_map,
            lambda prop_id, _category: registry_property_model(prop_id, self),
        )


@lru_cache(maxsize=1)
def iot_registry() -> YeelightIoTRegistry:
    """返回全局 Yeelight IoT registry 单例."""
    return YeelightIoTRegistry()


def is_iot_category(value: Any) -> bool:
    """判断值是否为 Yeelight IoT 品类."""
    return iot_registry().is_iot_category(value)


def platform_for_category(category: Any, *, default: str | None = None) -> str | None:
    """返回 IoT category 对应的 HA 平台名."""
    return iot_registry().platform_for_category(category, default=default)


def component_platform_hint(component: Any, *, default: str | None = None) -> str | None:
    """返回组件的 HA 平台提示."""
    return iot_registry().component_platform_hint(component, default=default)


def property_spec(prop: Any) -> IoTPropertySpec | None:
    """返回属性物模型定义."""
    return iot_registry().property_spec(prop)


def property_capability(prop: Any) -> PropertyCapability | None:
    """返回属性能力定义."""
    return iot_registry().property_capability(prop)


def normalize_property_key(prop: Any) -> str | None:
    """Normalize documented property names to the canonical runtime key."""
    key = to_str(prop)
    if key is None:
        return None
    return PROPERTY_ALIASES.get(key, key)


def normalize_event_type(value: Any) -> str | None:
    """将后台事件名/id 归一化为稳定 snake_case 事件类型."""
    return iot_registry().normalize_event_type(value)


def connection_protocol(value: Any) -> IoTProtocolSpec | None:
    """按协议 key 或 id 查询连接协议."""
    return iot_registry().protocol(value)


def node_type(value: Any) -> int | None:
    """返回 open platform nodeType 编号."""
    return iot_registry().node_type(value)


def product_spec(pid: Any) -> IoTProductSpec | None:
    """返回 pid 对应的产品构成定义."""
    return iot_registry().product_spec(pid)


def normalize_product_pid(pid: Any) -> int | None:
    """归一化易来产品 pid."""
    return _normalize_product_pid(pid)


def product_components(pid: Any) -> tuple[IoTComponentSpec, ...]:
    """返回 pid 声明的普通组件定义."""
    return iot_registry().product_components(pid)


def product_projectable_global_components(pid: Any) -> tuple[IoTComponentSpec, ...]:
    """返回 pid 声明且可安全投影的全局组件定义."""
    return iot_registry().product_projectable_global_components(pid)


def is_projectable_global_component(component: Any) -> bool:
    """判断全局组件是否有明确安全的 HA 投影语义."""
    return _is_projectable_global_component(component)


def product_category_candidates(pid: Any) -> tuple[str, ...]:
    """返回产品构成声明出的 IoT 品类候选."""
    return iot_registry().product_category_candidates(pid)


def product_protocols(pid: Any) -> tuple[IoTProtocolSpec, ...]:
    """返回产品构成声明出的连接协议定义."""
    return iot_registry().product_protocols(pid)


def product_hydration_properties(pid: Any) -> tuple[str, ...]:
    """返回产品构成声明出的属性读取集合."""
    return iot_registry().product_hydration_properties(pid)


def product_model_from_catalog(pid: Any) -> Any | None:
    """从产品构成目录构建 canonical 产品模型."""
    return iot_registry().product_model_from_catalog(pid)


def format_component_property_key(component_index: int | None, prop_name: Any) -> str:
    """格式化组件属性 key，形如 ``1-p``.

    ``component_index`` 为 None 时保留旧 payload 的直接属性名。
    """
    prop = to_str(prop_name)
    if prop is None:
        raise ValueError("prop_name must not be empty")
    if component_index is None:
        return prop
    if not isinstance(component_index, int) or component_index < 0:
        raise ValueError("component_index must be a non-negative integer or None")
    return f"{component_index}-{prop}"


def parse_component_property_key(value: Any) -> ControlKey:
    """解析组件属性 key，支持 ``1-p`` 和旧式 ``p``."""
    text = to_str(value)
    if text is None:
        raise ValueError("component property key must not be empty")
    match = _KEY_RE.match(text)
    if match is None:
        return ControlKey(component_index=None, prop_name=text)
    return ControlKey(
        component_index=int(match.group("index")),
        prop_name=match.group("prop"),
    )


def normalize_alias_key(value: Any) -> str:
    """归一化别名 key，供事件和协议查询复用."""
    text = to_str(value)
    if not text:
        return ""
    return _NON_ALNUM_RE.sub("_", text.lower()).strip("_")


def _component_key(value: Any) -> str:
    """归一化组件查询 key."""
    text = to_str(value)
    if not text:
        return ""
    return re.sub(r"[\s_-]+", " ", text.lower()).strip()


def _component_keys(component: IoTComponentSpec) -> tuple[str, ...]:
    """返回组件可查询 key，兼容别名、中文名和数字 id."""
    keys = {
        _component_key(component.alias),
        _component_key(component.name),
        _component_key(component.component_id),
    }
    return tuple(key for key in keys if key)


def _build_event_aliases(events: tuple[IoTEventSpec, ...]) -> dict[str | int, str]:
    """根据事件定义构建别名索引."""
    aliases: dict[str | int, str] = {}
    for item in events:
        aliases[normalize_alias_key(item.event_type)] = item.normalized
        aliases[normalize_alias_key(item.normalized)] = item.normalized
        if item.event_id is not None:
            aliases[item.event_id] = item.normalized
            aliases[str(item.event_id)] = item.normalized
        for alias in item.aliases:
            aliases[normalize_alias_key(alias)] = item.normalized
    return aliases
