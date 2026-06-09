"""Yeelight Pro 能力映射注册表."""

from .events import EVENT_TYPE_ALIASES, normalize_event_type
from .mapping import (
    CATEGORY_PLATFORM_MAP,
    COMPONENT_PLATFORM_HINTS,
    component_platform_hint,
    platform_for_category,
)
from .models import (
    ControlKey,
    IoTCategorySpec,
    IoTComponentSpec,
    IoTEventSpec,
    IoTPropertySpec,
    IoTProtocolSpec,
    PropertyCapability,
)
from .properties import PROPERTY_CAPABILITIES, property_capability
from .registry import (
    connection_protocol,
    format_component_property_key,
    iot_registry,
    is_iot_category,
    node_type,
    parse_component_property_key,
    property_spec,
)
from .validation import validate_iot_registry

__all__ = [
    "CATEGORY_PLATFORM_MAP",
    "COMPONENT_PLATFORM_HINTS",
    "ControlKey",
    "EVENT_TYPE_ALIASES",
    "IoTCategorySpec",
    "IoTComponentSpec",
    "IoTEventSpec",
    "IoTPropertySpec",
    "IoTProtocolSpec",
    "PROPERTY_CAPABILITIES",
    "PropertyCapability",
    "component_platform_hint",
    "connection_protocol",
    "format_component_property_key",
    "iot_registry",
    "is_iot_category",
    "node_type",
    "normalize_event_type",
    "parse_component_property_key",
    "platform_for_category",
    "property_capability",
    "property_spec",
    "validate_iot_registry",
]
