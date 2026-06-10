"""Yeelight Pro climate 投影模块.

将协调器运行时数据投影为 Home Assistant climate 实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from .device import flatten_instance_state, project_payload_device_info


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
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_climate(
    device_payload: Mapping[str, Any], *, domain: str
) -> HAClimateProjection | None:
    """将协调器载荷投影为 Home Assistant climate 视图。"""
    instance = _load_instance(device_payload)
    component = _select_climate_component(instance)
    if component is None and device_payload.get("type") != "climate":
        return None

    device_id = str(device_payload.get("device_id", "unknown"))
    params = _runtime_state(device_payload, instance, component)
    power = _bool(params.get("aco", params.get("p")), default=False)
    available = _bool(device_payload.get("online"), default=False)
    if instance is not None:
        available = bool(instance.online)
    if instance is not None and component is not None:
        available = bool(instance.online and component.available)

    return HAClimateProjection(
        component_id="climate",
        unique_id=f"{domain}_{device_id}_climate",
        name=None,
        available=available,
        current_temperature=_float(params.get("acct", params.get("t"))),
        target_temperature=_float(params.get("actt")),
        hvac_mode=HVACMode.AUTO if power else HVACMode.OFF,
        hvac_modes=[HVACMode.OFF, HVACMode.AUTO],
        supported_features=ClimateEntityFeature.TARGET_TEMPERATURE,
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
            category in {"climate", "air_conditioner", "bath_heater"}
            or component.component_id.lower() in {"climate", "air_conditioner", "bath_heater"}
            or any(key in component.state for key in ("acm", "actt", "acct", "acf", "aco"))
        ):
            return component
    return None


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
