"""将 canonical 产品/运行时数据投影为 Home Assistant event 视图."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.components.event import EventDeviceClass

from ..const import DOMAIN
from ..utils import to_bool
from .common import load_instance as _load_instance
from .common import load_product_model as _load_product_model
from .device import project_payload_device_info
from .event_helpers import component_available as _component_available
from .event_helpers import event_components as _event_components
from .event_helpers import event_device_class as _event_device_class
from .event_helpers import event_fallback_projection as _event_fallback_projection
from .event_helpers import event_icon as _event_icon
from .event_helpers import event_name as _event_name
from .event_helpers import event_types as _event_types


@dataclass(slots=True)
class HAEventProjection:
    """投影后的 Home Assistant event 实体视图."""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    event_types: list[str]
    device_info: dict[str, Any] | None
    device_class: EventDeviceClass | None = None
    icon: str | None = None


@dataclass(slots=True)
class HADeviceTriggerProjection:
    """投影后的 Home Assistant device trigger 视图."""

    component_id: str
    type: str
    subtype: str


def project_events(device_payload: Mapping[str, Any], *, domain: str) -> list[HAEventProjection]:
    """将 coordinator 设备数据投影为 Home Assistant event 实体列表."""
    instance = _load_instance(device_payload)
    product_model = _load_product_model(device_payload)
    if product_model is None:
        return []

    source_device_id = (
        instance.device_id
        if instance is not None
        else str(device_payload.get("device_id", "unknown"))
    )
    available = to_bool(
        instance.online if instance is not None else device_payload.get("online"),
        default=True,
    )
    instance_components = {
        component.component_id: component for component in (instance.components if instance else [])
    }
    event_components = _event_components(product_model, device_payload)
    device_info = project_payload_device_info(device_payload, instance)

    projections: list[HAEventProjection] = []
    total = len(event_components)
    for component in event_components:
        component_instance = instance_components.get(component.component_id)
        projections.append(
            HAEventProjection(
                component_id=component.component_id,
                unique_id=f"{domain}_{source_device_id}_{component.component_id}_event",
                name=_event_name(
                    component,
                    total=total,
                    product_model=product_model,
                    device_payload=device_payload,
                ),
                available=available and _component_available(
                    component_instance,
                    component,
                ),
                event_types=_event_types(component),
                device_info=device_info,
                device_class=_event_device_class(component, product_model),
                icon=_event_icon(component, product_model),
            )
        )
    if not projections:
        fallback = _event_fallback_projection(
            device_payload,
            product_model,
            instance,
            domain=domain,
        )
        if fallback is not None:
            projections.append(fallback)
    return projections


def project_device_triggers(device_payload: Mapping[str, Any]) -> list[HADeviceTriggerProjection]:
    """投影 event 类型设备支持的 Home Assistant device trigger 列表."""
    product_model = _load_product_model(device_payload)
    if product_model is None:
        return []

    triggers: list[HADeviceTriggerProjection] = []
    for component in _event_components(product_model, device_payload):
        for event_type in _event_types(component):
            triggers.append(
                HADeviceTriggerProjection(
                    component_id=component.component_id,
                    type=component.component_id,
                    subtype=event_type,
                )
            )
    if triggers:
        return triggers

    fallback = _event_fallback_projection(
        device_payload,
        product_model,
        _load_instance(device_payload),
        domain=DOMAIN,
    )
    if fallback is not None:
        for event_type in fallback.event_types:
            triggers.append(
                HADeviceTriggerProjection(
                    component_id=fallback.component_id,
                    type=fallback.component_id,
                    subtype=event_type,
                )
            )
    return triggers
