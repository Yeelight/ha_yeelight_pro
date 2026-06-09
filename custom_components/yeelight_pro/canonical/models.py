"""Canonical Home Assistant models for the Yeelight Pro integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from ..utils import normalize_scale, normalize_zoom
from ..utils import normalize_unit
from ..utils import to_int


def _list(value: Any) -> list[Any]:
    """Return a normalized list value."""
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    """Return a normalized dict value."""
    return value if isinstance(value, dict) else {}


def _value_list(value: Any) -> list[ValueItemModel]:
    """Return value-list metadata with stable non-empty unique codes."""
    items: list[ValueItemModel] = []
    seen_codes: set[str] = set()
    for item in _list(value):
        if not isinstance(item, dict):
            continue
        model = ValueItemModel.from_dict(item)
        if not model.code or model.code in seen_codes:
            continue
        seen_codes.add(model.code)
        items.append(model)
    return items


@dataclass(slots=True)
class ValueRangeModel:
    """Numeric range metadata."""

    min: int | None = None
    max: int | None = None
    step: int | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> ValueRangeModel | None:
        if not payload:
            return None
        minimum = to_int(payload.get("min"))
        maximum = to_int(payload.get("max"))
        step = to_int(payload.get("step"))
        if minimum is None and maximum is None and step is None:
            return None
        return cls(
            min=minimum,
            max=maximum,
            step=step,
        )


@dataclass(slots=True)
class ValueItemModel:
    """Enum-like value metadata."""

    code: str
    desc: str | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ValueItemModel:
        return cls(
            code=str(payload.get("code", "")).strip(),
            desc=payload.get("desc"),
        )


@dataclass(slots=True)
class PropertyModel:
    """Canonical component property definition."""

    prop_id: str
    name: str | None = None
    desc: str | None = None
    semantic: str | None = None
    kind: str | None = None
    property_type: str | None = None
    format: str | None = None
    unit: str | None = None
    zoom: int = 1
    scale: int = 1
    access: str | None = None
    default: Any = None
    value_range: ValueRangeModel | None = None
    value_list: list[ValueItemModel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PropertyModel:
        return cls(
            prop_id=str(payload.get("prop_id", payload.get("propId", ""))),
            name=payload.get("name"),
            desc=payload.get("desc"),
            semantic=payload.get("semantic"),
            kind=payload.get("kind"),
            property_type=payload.get("property_type", payload.get("propertyType")),
            format=payload.get("format"),
            unit=normalize_unit(payload.get("unit")),
            zoom=normalize_zoom(payload.get("zoom")),
            scale=normalize_scale(payload.get("scale")),
            access=payload.get("access"),
            default=payload.get("default", payload.get("value")),
            value_range=ValueRangeModel.from_dict(
                payload.get("value_range", payload.get("valueRange"))
            ),
            value_list=_value_list(payload.get("value_list", payload.get("valueList"))),
        )


@dataclass(slots=True)
class EventModel:
    """Canonical component event definition."""

    event_id: int | None = None
    name: str | None = None
    desc: str | None = None
    semantic: str | None = None
    params: list[PropertyModel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EventModel:
        return cls(
            event_id=payload.get("event_id", payload.get("eventId")),
            name=payload.get("name"),
            desc=payload.get("desc"),
            semantic=payload.get("semantic"),
            params=[
                PropertyModel.from_dict(item)
                for item in _list(payload.get("params"))
                if isinstance(item, dict)
            ],
        )


@dataclass(slots=True)
class ActionParamModel:
    """Canonical action parameter definition."""

    prop_id: str
    name: str | None = None
    desc: str | None = None
    format: str | None = None
    unit: str | None = None
    zoom: int = 1
    scale: int = 1
    default: Any = None
    value_range: ValueRangeModel | None = None
    value_list: list[ValueItemModel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ActionParamModel:
        return cls(
            prop_id=str(payload.get("prop_id", payload.get("propId", ""))),
            name=payload.get("name"),
            desc=payload.get("desc"),
            format=payload.get("format"),
            unit=normalize_unit(payload.get("unit")),
            zoom=normalize_zoom(payload.get("zoom")),
            scale=normalize_scale(payload.get("scale")),
            default=payload.get("default", payload.get("value")),
            value_range=ValueRangeModel.from_dict(
                payload.get("value_range", payload.get("valueRange"))
            ),
            value_list=_value_list(payload.get("value_list", payload.get("valueList"))),
        )


@dataclass(slots=True)
class ActionModel:
    """Canonical action definition."""

    action_name: str
    name: str | None = None
    desc: str | None = None
    semantic: str | None = None
    scope: str = "component"
    targets: list[str] = field(default_factory=list)
    params: list[ActionParamModel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ActionModel:
        return cls(
            action_name=str(payload.get("action_name", payload.get("actionName", ""))),
            name=payload.get("name"),
            desc=payload.get("desc"),
            semantic=payload.get("semantic"),
            scope=str(payload.get("scope", "component")),
            targets=[str(item) for item in _list(payload.get("targets"))],
            params=[
                ActionParamModel.from_dict(item)
                for item in _list(payload.get("params"))
                if isinstance(item, dict)
            ],
        )


@dataclass(slots=True)
class BridgeModel:
    """Canonical bridge capability definition."""

    protocols: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> BridgeModel | None:
        if not payload:
            return None
        return cls(protocols=[str(item) for item in _list(payload.get("protocols"))])


@dataclass(slots=True)
class ProductModel:
    """Canonical product metadata."""

    model_id: str
    manufacturer: str | None = None
    model: str | None = None
    description: str | None = None
    category: str | None = None
    categories: list[str] = field(default_factory=list)
    bridge: BridgeModel | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProductModel:
        return cls(
            model_id=str(payload.get("model_id", payload.get("modelId", ""))),
            manufacturer=payload.get("manufacturer"),
            model=payload.get("model"),
            description=payload.get("description"),
            category=payload.get("category"),
            categories=[str(item) for item in _list(payload.get("categories"))],
            bridge=BridgeModel.from_dict(payload.get("bridge")),
        )


@dataclass(slots=True)
class ComponentModel:
    """Canonical component definition."""

    component_id: str
    cid: int | None = None
    index: int | None = None
    name: str | None = None
    desc: str | None = None
    component_type: str | None = None
    category: str | None = None
    capabilities: list[str] = field(default_factory=list)
    properties: list[PropertyModel] = field(default_factory=list)
    events: list[EventModel] = field(default_factory=list)
    actions: list[ActionModel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ComponentModel:
        return cls(
            component_id=str(payload.get("component_id", payload.get("componentId", ""))),
            cid=payload.get("cid"),
            index=payload.get("index"),
            name=payload.get("name"),
            desc=payload.get("desc"),
            component_type=payload.get("component_type", payload.get("componentType")),
            category=payload.get("category"),
            capabilities=[str(item) for item in _list(payload.get("capabilities"))],
            properties=[
                PropertyModel.from_dict(item)
                for item in _list(payload.get("properties"))
                if isinstance(item, dict)
            ],
            events=[
                EventModel.from_dict(item)
                for item in _list(payload.get("events"))
                if isinstance(item, dict)
            ],
            actions=[
                ActionModel.from_dict(item)
                for item in _list(payload.get("actions"))
                if isinstance(item, dict)
            ],
        )


@dataclass(slots=True)
class HAProductModel:
    """Top-level canonical product model."""

    schema_version: str
    product: ProductModel
    components: list[ComponentModel] = field(default_factory=list)
    device_actions: list[ActionModel] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to a plain dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HAProductModel:
        return cls(
            schema_version=str(payload.get("schema_version", payload.get("schemaVersion", "v1"))),
            product=ProductModel.from_dict(_dict(payload.get("product"))),
            components=[
                ComponentModel.from_dict(item)
                for item in _list(payload.get("components"))
                if isinstance(item, dict)
            ],
            device_actions=[
                ActionModel.from_dict(item)
                for item in _list(payload.get("device_actions", payload.get("deviceActions")))
                if isinstance(item, dict)
            ],
            notes=[str(item) for item in _list(payload.get("notes"))],
        )


_DEVICE_INSTANCE_EXPORTS = {
    "ComponentInstanceModel",
    "DeviceInfoModel",
    "HADeviceInstanceModel",
    "InstanceCapabilitiesModel",
}


def __getattr__(name: str) -> Any:
    """Lazily expose moved runtime instance models for import compatibility."""
    if name in _DEVICE_INSTANCE_EXPORTS:
        from . import device_instance

        return getattr(device_instance, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
