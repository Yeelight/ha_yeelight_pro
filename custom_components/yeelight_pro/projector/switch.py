"""将协调器运行时数据投影为 Home Assistant switch 视图.

迁移自 lucore_gateway/projector/switch.py，
使用 yeelight_pro.utils 提供的通用工具函数。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import HADeviceInstanceModel
from ..entity_category import entity_category_for_property
from ..utils import to_bool, to_str
from .common import (
    component_index,
    payload_available,
    product_component,
    schema_backed_component_available,
)
from .common import load_instance as _load_instance
from .common import load_product_model as _load_product_model
from .device import project_payload_device_info
from .switch_helpers import (
    _allows_raw_switch_fallback,
    _allows_switch_projection,
    _build_switch_name,
    _component_id_from_raw_key,
    _component_state_key_map,
    _direct_switch_prop,
    _extract_indexed_switch_keys,
    _index_from_raw_key,
    _looks_like_switch_component,
    _params,
    _resolve_component_control_key,
    _switch_channel_allowed,
)


@dataclass(slots=True)
class HASwitchProjection:
    """投影后的 Home Assistant switch 视图."""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    is_on: bool
    control_key: str
    device_info: dict[str, Any] | None
    icon: str | None = None
    entity_category: str | None = None


def project_switches(
    device_payload: Mapping[str, Any], *, domain: str
) -> list[HASwitchProjection]:
    """将协调器 payload 投影为一个或多个 Home Assistant switch 实体.

    优先基于实例模型投影，若无匹配则回退到原始参数投影。
    """
    instance = _load_instance(device_payload)
    projections = _project_instance_switches(device_payload, instance, domain=domain)
    if projections:
        return projections
    return _project_raw_switches(device_payload, instance, domain=domain)


# ---------------------------------------------------------------------------
# 实例模型投影
# ---------------------------------------------------------------------------


def _project_instance_switches(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    *,
    domain: str,
) -> list[HASwitchProjection]:
    """基于 HADeviceInstanceModel 投影 switch 组件."""
    if instance is None:
        return []
    if not _allows_switch_projection(device_payload):
        return []

    product_model = _load_product_model(device_payload)
    base_name = instance.name or to_str(device_payload.get("name"))
    device_info = project_payload_device_info(device_payload, instance)
    params = _params(device_payload)
    key_map = _component_state_key_map(instance)
    projections: list[HASwitchProjection] = []

    for component in instance.components:
        if not _looks_like_switch_component(component):
            continue
        if not _switch_channel_allowed(
            device_payload,
            component_index(component.component_id),
        ):
            continue
        if _extract_indexed_switch_keys(component.state):
            continue

        prop = _direct_switch_prop(component.state) or _schema_switch_prop(
            product_model,
            component.component_id,
        )
        if prop is None:
            continue

        value = component.state.get(prop)
        control_key = _resolve_component_control_key(
            component.component_id,
            prop,
            params=params,
            key_map=key_map,
        )
        projections.append(
            HASwitchProjection(
                component_id=component.component_id,
                unique_id=f"{domain}_{instance.device_id}_{component.component_id}",
                name=_build_switch_name(
                    base_name,
                    component.component_id,
                    control_key,
                    component,
                    device_payload=device_payload,
                ),
                available=schema_backed_component_available(
                    payload_available(device_payload, instance),
                    component,
                    schema_component=product_component(
                        product_model,
                        component.component_id,
                    ),
                ),
                is_on=bool(value),
                control_key=control_key,
                device_info=device_info,
                icon="mdi:light-switch",
                entity_category=entity_category_for_property(prop),
            )
        )

    return projections


def _schema_switch_prop(product_model: Any | None, component_id: str) -> str | None:
    """Return a switch control prop declared by product schema for this component."""
    if product_model is None:
        return None
    component = next(
        (
            item
            for item in product_model.components
            if item.component_id == component_id
        ),
        None,
    )
    if component is None:
        return None
    prop_ids = {prop.prop_id for prop in component.properties}
    for prop in ("p", "sp", "on"):
        if prop in prop_ids:
            return prop
    return None


# ---------------------------------------------------------------------------
# 原始参数投影（回退路径）
# ---------------------------------------------------------------------------


def _project_raw_switches(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    *,
    domain: str,
) -> list[HASwitchProjection]:
    """基于原始 params 投影 switch（无实例模型时的回退路径）."""
    params = _params(device_payload)
    device_id = str(device_payload.get("device_id", "unknown"))
    base_name = to_str(device_payload.get("name")) or device_id
    device_info = project_payload_device_info(device_payload, instance)
    available = to_bool(device_payload.get("online"), default=True)

    if not _allows_raw_switch_fallback(device_payload):
        return []

    raw_keys = _extract_indexed_switch_keys(params)
    if raw_keys:
        projections: list[HASwitchProjection] = []
        for raw_key in raw_keys:
            if not _switch_channel_allowed(device_payload, _index_from_raw_key(raw_key)):
                continue
            component_id = _component_id_from_raw_key(raw_key)
            projections.append(
                HASwitchProjection(
                    component_id=component_id,
                    unique_id=f"{domain}_{device_id}_{component_id}",
                    name=_build_switch_name(
                        base_name,
                        component_id,
                        raw_key,
                        device_payload=device_payload,
                    ),
                    available=available,
                    is_on=bool(params.get(raw_key)),
                    control_key=raw_key,
                    device_info=device_info,
                    icon="mdi:light-switch",
                    entity_category=entity_category_for_property(raw_key),
                )
            )
        if projections:
            return projections

    if device_payload.get("type") not in {"switch", "outlet"}:
        return []

    direct_prop = _direct_switch_prop(params) or "p"
    component_id = "switch"
    return [
        HASwitchProjection(
            component_id=component_id,
            unique_id=f"{domain}_{device_id}_{component_id}",
            name=base_name,
            available=available,
            is_on=bool(params.get(direct_prop, params.get("on", False))),
            control_key=direct_prop,
            device_info=device_info,
            icon="mdi:light-switch",
            entity_category=entity_category_for_property(direct_prop),
        )
    ]
