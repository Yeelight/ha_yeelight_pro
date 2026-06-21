"""将协调器运行时数据投影为 Home Assistant switch 视图.

迁移自 lucore_gateway/projector/switch.py，
使用 yeelight_pro.utils 提供的通用工具函数。
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..entity_category import entity_category_for_property
from ..identity import payload_entity_unique_id_prefix
from ..utils import to_bool, to_str
from .common import (
    component_index,
    component_property_value,
    payload_available,
    product_component,
    public_switch_component_id,
    schema_backed_component_available,
)
from .common import load_instance as _load_instance
from .common import load_product_model as _load_product_model
from .device import project_payload_device_info
from .switch_helpers import (
    _allows_component_switch_projection,
    _allows_raw_switch_fallback,
    _build_switch_name,
    _component_id_from_raw_key,
    _component_state_key_map,
    _direct_switch_prop,
    _extract_indexed_switch_keys,
    _index_from_raw_key,
    _looks_like_switch_component,
    _params,
    _prefers_switch_power_prop,
    _resolve_component_control_key,
    _switch_channel_allowed,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class HASwitchProjection:
    """投影后的 Home Assistant switch 视图."""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    is_on: bool | None
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
        _LOGGER.debug(
            "Skipping instance switch projection: device_id=%s reason=no_device_instance",
            device_payload.get("device_id"),
        )
        return []
    if not _allows_component_switch_projection(device_payload, instance):
        _LOGGER.debug(
            "Skipping component switch projection: device_id=%s category=%s "
            "reason=parent_category_blocks_switch_without_component_evidence",
            instance.device_id,
            device_payload.get("iot_category") or device_payload.get("category"),
        )
        return []

    product_model = _load_product_model(device_payload)
    base_name = instance.name or to_str(device_payload.get("name"))
    device_info = project_payload_device_info(device_payload, instance)
    unique_id_prefix = payload_entity_unique_id_prefix(device_payload, domain=domain)
    params = _params(device_payload)
    key_map = _component_state_key_map(instance)
    projections: list[HASwitchProjection] = []

    switch_component_position = 0
    for component in instance.components:
        schema_component = product_component(product_model, component.component_id)
        if not _looks_like_switch_component(component, schema_component):
            _log_switch_component_skip(
                instance,
                component,
                schema_component,
                "missing_switch_component_evidence",
            )
            continue
        if not _switch_channel_allowed(
            device_payload,
            component_index(component.component_id),
        ):
            _log_switch_component_skip(
                instance,
                component,
                schema_component,
                "channel_exceeds_product_hint",
            )
            continue
        if _extract_indexed_switch_keys(component.state):
            _log_switch_component_skip(
                instance,
                component,
                schema_component,
                "indexed_keys_projected_from_raw_params",
            )
            continue

        prop = _switch_prop_for_component(
            device_payload,
            product_model,
            component,
            schema_component,
        )
        if prop is None:
            prop = _direct_switch_prop(component.state) or _schema_switch_prop(
                product_model,
                component.component_id,
            )
        if prop is None:
            _log_switch_component_skip(
                instance,
                component,
                schema_component,
                "missing_switch_control_property",
            )
            continue

        switch_component_position += 1
        control_key = _resolve_component_control_key(
            component.component_id,
            prop,
            params=params,
            key_map=key_map,
        )
        control_key = _resolve_schema_component_control_key(
            control_key,
            prop,
            component_index=component_index(component.component_id)
            or switch_component_position,
            params=params,
        )
        public_component_id = public_switch_component_id(
            device_payload,
            component.component_id,
        )
        projections.append(
            HASwitchProjection(
                component_id=public_component_id,
                unique_id=f"{unique_id_prefix}_{instance.device_id}_{public_component_id}",
                name=_build_switch_name(
                    base_name,
                    public_component_id,
                    control_key,
                    component,
                    device_payload=device_payload,
                ),
                available=schema_backed_component_available(
                    payload_available(device_payload, instance),
                    component,
                    schema_component=schema_component,
                ),
                is_on=_switch_state_value(
                    component_property_value(params, instance, component, prop)
                ),
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
    for prop in ("p", "sp"):
        if prop in prop_ids:
            return prop
    return None


def _switch_prop_for_component(
    device_payload: Mapping[str, Any],
    product_model: Any | None,
    component: ComponentInstanceModel,
    schema_component: Any | None,
) -> str | None:
    """Resolve the documented switch property for this component."""
    prop_ids = set(component.state)
    if schema_component is not None:
        prop_ids.update(prop.prop_id for prop in schema_component.properties)
    if not prop_ids and product_model is not None:
        component_schema = product_component(product_model, component.component_id)
        if component_schema is not None:
            prop_ids.update(prop.prop_id for prop in component_schema.properties)

    if _prefers_switch_power_prop(device_payload, component, schema_component):
        for prop in ("sp", "p"):
            if prop in prop_ids:
                return prop
        return "sp"

    for prop in ("p", "sp"):
        if prop in prop_ids:
            return prop
    return None


def _resolve_schema_component_control_key(
    control_key: str,
    prop: str,
    *,
    component_index: int,
    params: Mapping[str, Any],
) -> str:
    """Map repeated schema switch components to indexed runtime control keys."""
    if control_key != prop or prop not in {"p", "sp"}:
        return control_key
    indexed_key = f"{component_index}-{prop}"
    if indexed_key in params or component_index > 1:
        return indexed_key
    return control_key


def _switch_state_value(value: Any) -> bool | None:
    """Return switch state while preserving unknown sparse component state."""
    if value is None:
        return None
    return bool(value)


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
    unique_id_prefix = payload_entity_unique_id_prefix(device_payload, domain=domain)
    base_name = to_str(device_payload.get("name")) or device_id
    device_info = project_payload_device_info(device_payload, instance)
    available = to_bool(device_payload.get("online"), default=True)

    if not _allows_raw_switch_fallback(device_payload):
        _LOGGER.debug(
            "Skipping raw switch projection: device_id=%s category=%s type=%s "
            "props=%s reason=raw_switch_not_supported_by_category_or_component",
            device_id,
            device_payload.get("iot_category") or device_payload.get("category"),
            device_payload.get("type"),
            sorted(str(key) for key in params),
        )
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
                    unique_id=f"{unique_id_prefix}_{device_id}_{component_id}",
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

    if device_payload.get("type") != "switch":
        _LOGGER.debug(
            "Skipping direct raw switch projection: device_id=%s category=%s "
            "type=%s props=%s reason=missing_indexed_keys_and_legacy_switch_type",
            device_id,
            device_payload.get("iot_category") or device_payload.get("category"),
            device_payload.get("type"),
            sorted(str(key) for key in params),
        )
        return []

    direct_prop = _direct_switch_prop(params) or "p"
    component_id = "switch"
    return [
        HASwitchProjection(
            component_id=component_id,
            unique_id=f"{unique_id_prefix}_{device_id}_{component_id}",
            name=base_name,
            available=available,
            is_on=bool(params.get(direct_prop, False)),
            control_key=direct_prop,
            device_info=device_info,
            icon="mdi:light-switch",
            entity_category=entity_category_for_property(direct_prop),
        )
    ]


def _log_switch_component_skip(
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    schema_component: Any | None,
    reason: str,
) -> None:
    """Log why a component did not become a switch entity."""
    _LOGGER.debug(
        "Skipping switch component projection: device_id=%s component_id=%s "
        "category=%s product_category=%s props=%s reason=%s",
        instance.device_id,
        component.component_id,
        component.category,
        None if schema_component is None else schema_component.category,
        sorted(str(key) for key in component.state),
        reason,
    )
