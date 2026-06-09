"""Canonical runtime device-instance models for Yeelight Pro."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from .models import _dict, _list

@dataclass(slots=True)
class InstanceCapabilitiesModel:
    """Resolved instance capability metadata."""

    features: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any] | None
    ) -> InstanceCapabilitiesModel | None:
        if not payload:
            return None
        return cls(
            features=[str(item) for item in _list(payload.get("features"))],
            constraints=_dict(payload.get("constraints")),
        )


@dataclass(slots=True)
class DeviceInfoModel:
    """HA-oriented device registry projection."""

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

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> DeviceInfoModel | None:
        if not payload:
            return None
        return cls(
            identifiers=[
                [str(item[0]), str(item[1])]
                for item in _list(payload.get("identifiers"))
                if isinstance(item, list) and len(item) == 2
            ],
            connections=[
                [str(item[0]), str(item[1])]
                for item in _list(payload.get("connections"))
                if isinstance(item, list) and len(item) == 2
            ],
            via_device=(
                [str(payload["via_device"][0]), str(payload["via_device"][1])]
                if isinstance(payload.get("via_device"), list)
                and len(payload["via_device"]) == 2
                else None
            ),
            manufacturer=payload.get("manufacturer"),
            model=payload.get("model"),
            model_id=payload.get("model_id", payload.get("modelId")),
            name=payload.get("name"),
            serial_number=payload.get("serial_number", payload.get("serialNumber")),
            sw_version=payload.get("sw_version", payload.get("swVersion")),
            hw_version=payload.get("hw_version", payload.get("hwVersion")),
            configuration_url=payload.get("configuration_url", payload.get("configurationUrl")),
            entry_type=payload.get("entry_type", payload.get("entryType")),
            suggested_area=payload.get("suggested_area", payload.get("suggestedArea")),
            default_manufacturer=payload.get(
                "default_manufacturer", payload.get("defaultManufacturer")
            ),
            default_model=payload.get("default_model", payload.get("defaultModel")),
            default_name=payload.get("default_name", payload.get("defaultName")),
            translation_key=payload.get("translation_key", payload.get("translationKey")),
            translation_placeholders=_dict(
                payload.get("translation_placeholders", payload.get("translationPlaceholders"))
            )
            or None,
        )


@dataclass(slots=True)
class ComponentInstanceModel:
    """Canonical component runtime state."""

    component_id: str
    component_type: str | None = None
    category: str | None = None
    available: bool = True
    instance_capabilities: InstanceCapabilitiesModel | None = None
    state: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ComponentInstanceModel:
        return cls(
            component_id=str(payload.get("component_id", payload.get("componentId", ""))),
            component_type=payload.get("component_type", payload.get("componentType")),
            category=payload.get("category"),
            available=bool(payload.get("available", True)),
            instance_capabilities=InstanceCapabilitiesModel.from_dict(
                payload.get("instance_capabilities", payload.get("instanceCapabilities"))
            ),
            state=_dict(payload.get("state")),
        )


@dataclass(slots=True)
class HADeviceInstanceModel:
    """Top-level canonical runtime device instance."""

    device_id: str
    name: str | None = None
    online: bool = True
    product_ref: dict[str, Any] = field(default_factory=dict)
    device_info: DeviceInfoModel | None = None
    components: list[ComponentInstanceModel] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to a plain dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HADeviceInstanceModel:
        return cls(
            device_id=str(payload.get("device_id", payload.get("deviceId", ""))),
            name=payload.get("name"),
            online=bool(payload.get("online", True)),
            product_ref=_dict(payload.get("product_ref", payload.get("productRef"))),
            device_info=DeviceInfoModel.from_dict(payload.get("device_info", payload.get("deviceInfo"))),
            components=[
                ComponentInstanceModel.from_dict(item)
                for item in _list(payload.get("components"))
                if isinstance(item, dict)
            ],
            extensions=_dict(payload.get("extensions")),
        )
