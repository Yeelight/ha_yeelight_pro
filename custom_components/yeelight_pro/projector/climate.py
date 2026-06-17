"""Yeelight Pro climate 投影模块.

将协调器运行时数据投影为 Home Assistant climate 实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping

from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from ..canonical.models import (
    ComponentInstanceModel,
    HADeviceInstanceModel,
    HAProductModel,
)
from ..identity import payload_entity_unique_id_prefix
from .common import (
    component_display_label,
    load_product_model,
    payload_available,
    product_component,
    schema_backed_component_available,
)
from .climate_helpers import climate_skip_reason
from .climate_projection import build_climate_projection
from .device import flatten_instance_state, project_payload_device_info
from .platform_evidence import (
    component_has_climate_evidence,
    component_prop_ids,
    payload_has_climate_evidence,
)
from .property_control_common import control_key

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class HAClimateProjection:
    """投影后的 Home Assistant climate 实体视图。"""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    current_temperature: float | None
    target_temperature: float | None
    hvac_mode: HVACMode
    hvac_modes: list[HVACMode]
    supported_features: ClimateEntityFeature
    power_key: str | None
    target_temperature_key: str | None
    mode_key: str | None
    fan_mode_key: str | None
    fan_mode: str | None
    fan_modes: list[str]
    fan_mode_values: dict[str, int]
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_climate(
    device_payload: Mapping[str, Any], *, domain: str
) -> HAClimateProjection | None:
    """将协调器载荷投影为 Home Assistant climate 视图。"""
    climates = project_climates(device_payload, domain=domain)
    return climates[0] if climates else None


def project_climates(
    device_payload: Mapping[str, Any], *, domain: str
) -> list[HAClimateProjection]:
    """将协调器载荷投影为一个或多个 Home Assistant climate 视图。"""
    instance = _load_instance(device_payload)
    product_model = load_product_model(device_payload)
    if instance is None:
        legacy = _project_legacy_climate(device_payload, domain=domain)
        return [legacy] if legacy is not None else []

    components = _climate_components(instance, product_model)
    return [
        _project_instance_climate(
            device_payload,
            instance,
            component,
            product_model=product_model,
            total=len(components),
            domain=domain,
        )
        for component in components
    ]


def _project_legacy_climate(
    device_payload: Mapping[str, Any], *, domain: str
) -> HAClimateProjection | None:
    """兼容旧版扁平 temp_control payload 的 climate 投影。"""
    params = _params(device_payload)
    if not _payload_is_climate(device_payload, params):
        _LOGGER.debug(
            "Skipping legacy climate projection: device_id=%s category=%s type=%s "
            "props=%s reason=%s",
            device_payload.get("device_id"),
            device_payload.get("category"),
            device_payload.get("type"),
            sorted(str(key) for key in params),
            _payload_climate_skip_reason(device_payload, params),
        )
        return None

    device_id = str(device_payload.get("device_id", "unknown"))
    unique_id_prefix = payload_entity_unique_id_prefix(device_payload, domain=domain)
    return build_climate_projection(
        HAClimateProjection,
        component_id="climate",
        unique_id=f"{unique_id_prefix}_{device_id}_climate",
        name="温控",
        available=payload_available(device_payload),
        state=params,
        power_key=_first_available_property(params, None, ("acp", "p", "rfhp")),
        target_temperature_key=_first_available_property(
            params,
            None,
            ("actt", "tgt", "rfhtt"),
        ),
        mode_key=_first_available_property(params, None, ("acm",)),
        fan_mode_key=_first_available_property(params, None, ("acf",)),
        current_temperature_key=_first_available_property(
            params,
            None,
            ("acct", "t", "rfhct"),
        ),
        schema_component=None,
        device_info=project_payload_device_info(device_payload),
    )


def _project_instance_climate(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    *,
    product_model: HAProductModel | None,
    total: int,
    domain: str,
) -> HAClimateProjection:
    """投影单个 canonical temp-control component."""
    params = _runtime_state(device_payload, instance, component)
    schema_component = product_component(product_model, component.component_id)
    available = schema_backed_component_available(
        payload_available(device_payload, instance),
        component,
        schema_component=schema_component,
    )
    power_prop = _first_available_property(
        params,
        component,
        ("acp", "p", "rfhp"),
    )
    target_prop = _first_available_property(
        params,
        component,
        ("actt", "tgt", "rfhtt"),
    )
    current_prop = _first_available_property(
        params,
        component,
        ("acct", "t", "rfhct"),
    )
    mode_prop = _first_available_property(params, component, ("acm",))
    fan_prop = _first_available_property(params, component, ("acf",))
    return build_climate_projection(
        HAClimateProjection,
        component_id=component.component_id,
        unique_id=_project_climate_unique_id(
            device_payload,
            instance,
            component,
            total=total,
            domain=domain,
        ),
        name=_project_climate_name(component, total=total),
        available=available,
        state=params,
        power_key=(
            control_key(instance, component.component_id, power_prop)
            if power_prop is not None
            else None
        ),
        target_temperature_key=(
            control_key(instance, component.component_id, target_prop)
            if target_prop is not None
            else None
        ),
        mode_key=(
            control_key(instance, component.component_id, mode_prop)
            if mode_prop is not None
            else None
        ),
        fan_mode_key=(
            control_key(instance, component.component_id, fan_prop)
            if fan_prop is not None
            else None
        ),
        current_temperature_key=current_prop,
        schema_component=schema_component,
        device_info=project_payload_device_info(device_payload, instance),
    )


# -- 辅助函数 ---------------------------------------------------------------


def _load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从载荷中解析 HADeviceInstanceModel 实例。"""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """从载荷中提取 params 字段。"""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _climate_components(
    instance: HADeviceInstanceModel | None,
    product_model: HAProductModel | None,
) -> list[ComponentInstanceModel]:
    """返回所有具备 climate 证据的组件，按原始组件顺序稳定排序。"""
    if instance is None:
        return []

    components: list[ComponentInstanceModel] = []
    for component in instance.components:
        schema_component = product_component(product_model, component.component_id)
        if component_has_climate_evidence(component, schema_component):
            components.append(component)
            continue
        _LOGGER.debug(
            "Skipping climate component projection: device_id=%s component_id=%s "
            "category=%s product_category=%s props=%s reason=%s",
            instance.device_id,
            component.component_id,
            component.category,
            None if schema_component is None else schema_component.category,
            sorted(component_prop_ids(component, schema_component)),
            _climate_component_skip_reason(component, schema_component),
        )
    return components


def _payload_is_climate(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Return true only for documented climate/temp-control runtime categories."""
    return payload_has_climate_evidence(device_payload, state)


def _payload_climate_skip_reason(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> str:
    """Return why a flat payload cannot be projected as climate."""
    return climate_skip_reason(
        set(state),
        has_evidence=payload_has_climate_evidence(device_payload, state),
    )


def _climate_component_skip_reason(
    component: ComponentInstanceModel,
    schema_component: Any | None,
) -> str:
    """Return why a component was not projected as climate."""
    props = component_prop_ids(component, schema_component)
    return climate_skip_reason(props, has_evidence=False)


def _runtime_state(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    component: ComponentInstanceModel | None,
) -> dict[str, Any]:
    """合并载荷 params 与组件/实例状态。"""
    if component is not None:
        merged = _params(device_payload)
        merged.update(component.state)
        return merged

    state = flatten_instance_state(instance)
    if state:
        return state
    return _params(device_payload)


def _first_available_property(
    params: Mapping[str, Any],
    component: ComponentInstanceModel | None,
    candidates: tuple[str, ...],
) -> str | None:
    """按当前状态和 schema 顺序选择可用属性."""
    component_props = set(component.state) if component is not None else set()
    for candidate in candidates:
        if candidate in params or candidate in component_props:
            return candidate
    return None


def _project_climate_name(
    component: ComponentInstanceModel,
    *,
    total: int,
) -> str | None:
    """Return HA climate entity name, preserving single-climate compatibility."""
    if total <= 1 and component.component_id in {"air_conditioner", "climate"}:
        return "温控"
    return component_display_label(component)


def _project_climate_unique_id(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    *,
    total: int,
    domain: str,
) -> str:
    """Return stable unique_id with the runtime identity scope applied."""
    unique_id_prefix = payload_entity_unique_id_prefix(device_payload, domain=domain)
    if total <= 1 and component.component_id in {"air_conditioner", "climate"}:
        return f"{unique_id_prefix}_{instance.device_id}_climate"
    return f"{unique_id_prefix}_{instance.device_id}_{component.component_id}_climate"

__all__ = ["HAClimateProjection", "project_climate", "project_climates"]
