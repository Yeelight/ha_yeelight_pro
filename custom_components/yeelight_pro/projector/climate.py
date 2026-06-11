"""Yeelight Pro climate 投影模块.

将协调器运行时数据投影为 Home Assistant climate 实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..utils import to_category
from .common import (
    load_product_model,
    payload_available,
    product_component,
    schema_backed_component_available,
)
from .device import flatten_instance_state, project_payload_device_info
from .property_control_common import control_key


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
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_climate(
    device_payload: Mapping[str, Any], *, domain: str
) -> HAClimateProjection | None:
    """将协调器载荷投影为 Home Assistant climate 视图。"""
    instance = _load_instance(device_payload)
    component = _select_climate_component(instance)
    if component is None and not _payload_is_climate(device_payload):
        return None

    device_id = str(device_payload.get("device_id", "unknown"))
    params = _runtime_state(device_payload, instance, component)
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
    power = _bool(params.get(power_prop), default=False) if power_prop else False
    available = payload_available(device_payload, instance)
    if instance is not None and component is not None:
        product_model = load_product_model(device_payload)
        available = schema_backed_component_available(
            payload_available(device_payload, instance),
            component,
            schema_component=product_component(product_model, component.component_id),
        )

    return HAClimateProjection(
        component_id="climate",
        unique_id=f"{domain}_{device_id}_climate",
        name="温控",
        available=available,
        current_temperature=_float(params.get(current_prop)) if current_prop else None,
        target_temperature=_float(params.get(target_prop)) if target_prop else None,
        hvac_mode=HVACMode.AUTO if power else HVACMode.OFF,
        hvac_modes=[HVACMode.OFF, HVACMode.AUTO],
        supported_features=ClimateEntityFeature.TARGET_TEMPERATURE,
        power_key=(
            control_key(instance, component.component_id, power_prop)
            if instance is not None and component is not None and power_prop is not None
            else power_prop
        ),
        target_temperature_key=(
            control_key(instance, component.component_id, target_prop)
            if instance is not None and component is not None and target_prop is not None
            else target_prop
        ),
        device_info=project_payload_device_info(device_payload, instance),
        icon="mdi:air-conditioner",
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


def _select_climate_component(
    instance: HADeviceInstanceModel | None,
) -> ComponentInstanceModel | None:
    """选择 climate 相关组件（空调/暖风机等）。"""
    if instance is None:
        return None

    for component in instance.components:
        category = _string(component.category).lower()
        if (
            category in {
                "climate",
                "temp_control",
                "air_conditioner",
                "air conditioner",
                "bath_heater",
                "floor_heating",
                "floor heating",
            }
            or component.component_id.lower()
            in {
                "climate",
                "temp_control",
                "air_conditioner",
                "bath_heater",
                "floor_heating",
            }
            or any(
                key in component.state
                for key in (
                    "acm",
                    "actt",
                    "acct",
                    "acf",
                    "tgt",
                    "rfhp",
                    "rfhtt",
                    "rfhct",
                )
            )
        ):
            return component
    return None


def _payload_is_climate(device_payload: Mapping[str, Any]) -> bool:
    """Return true only for documented climate/temp-control runtime categories."""
    category = to_category(
        device_payload.get("iot_category")
        or device_payload.get("category")
        or device_payload.get("type")
    )
    return category in {"climate", "temp_control", "air_conditioner", "bath_heater"}


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


def _bool(value: Any, *, default: bool) -> bool:
    """安全布尔值转换。"""
    if value is None:
        return default
    return bool(value)


def _float(value: Any) -> float | None:
    """安全浮点数转换。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string(value: Any) -> str:
    """安全字符串转换。"""
    if value is None:
        return ""
    return str(value).strip()
