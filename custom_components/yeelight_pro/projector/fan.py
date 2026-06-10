"""Yeelight Pro 风扇投影模块.

将设备运行时数据投影为 Home Assistant 风扇实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.components.fan import FanEntityFeature

from ..utils import to_bool, to_str
from .common import (
    NumericRange,
    load_instance as _load_instance,
    load_product_model as _load_product_model,
    product_component as _product_component,
)
from .device import project_payload_device_info
from .fan_helpers import (
    _direction_key,
    _direction_support,
    _fallback_direction_support,
    _fallback_speed_range,
    _is_on,
    _looks_like_fan_component,
    _mode_key,
    _params,
    _power_key,
    _preset_modes,
    _project_fan_name,
    _project_percentage,
    _resolve_control_key,
    _speed_count,
    _speed_key,
    _speed_range,
    _state_text,
    _supported_features,
)


@dataclass(slots=True)
class HAFanProjection:
    """设备运行时数据投影后的 Home Assistant 风扇视图。"""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    is_on: bool
    percentage: int | None
    speed_count: int
    preset_mode: str | None
    preset_modes: list[str] | None
    current_direction: str | None
    supported_features: FanEntityFeature
    power_key: str | None
    speed_key: str | None
    mode_key: str | None
    direction_key: str | None
    speed_range: NumericRange | None
    direction_values: dict[str, Any]
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_fans(device_payload: Mapping[str, Any], *, domain: str) -> list[HAFanProjection]:
    """将协调器设备载荷投影为 Home Assistant 风扇视图。"""
    instance = _load_instance(device_payload)
    if instance is None:
        projection = _project_legacy_fan(device_payload, domain=domain)
        return [projection] if projection is not None else []

    product_model = _load_product_model(device_payload)
    params = _params(device_payload)
    device_info = project_payload_device_info(device_payload, instance)
    projections: list[HAFanProjection] = []

    for component in instance.components:
        product_component = _product_component(product_model, component.component_id)
        if not _looks_like_fan_component(component, product_component):
            continue

        state = dict(component.state)
        power_key = _resolve_control_key(
            component.component_id,
            _power_key(state, product_component),
            params,
        )
        speed_key = _resolve_control_key(
            component.component_id,
            _speed_key(state, product_component),
            params,
        )
        mode_key = _resolve_control_key(
            component.component_id,
            _mode_key(state, product_component),
            params,
        )
        direction_key = _resolve_control_key(
            component.component_id,
            _direction_key(state, product_component),
            params,
        )

        speed_range = _speed_range(component, product_component, state)
        preset_modes = _preset_modes(component, product_component, state)
        current_direction, direction_values = _direction_support(
            component,
            product_component,
            state,
        )
        supported_features = _supported_features(
            power_key=power_key,
            speed_key=speed_key,
            mode_key=mode_key,
            preset_modes=preset_modes,
            direction_key=direction_key,
            direction_values=direction_values,
        )

        projections.append(
            HAFanProjection(
                component_id=component.component_id,
                unique_id=f"{domain}_{instance.device_id}_{component.component_id}",
                name=_project_fan_name(component),
                available=bool(instance.online and component.available),
                is_on=_is_on(state, power_key, speed_key, mode_key),
                percentage=_project_percentage(state, speed_key, speed_range),
                speed_count=_speed_count(speed_range),
                preset_mode=_state_text(state, mode_key),
                preset_modes=preset_modes,
                current_direction=current_direction,
                supported_features=supported_features,
                power_key=power_key,
                speed_key=speed_key,
                mode_key=mode_key,
                direction_key=direction_key,
                speed_range=speed_range,
                direction_values=direction_values,
                device_info=device_info,
                icon="mdi:fan",
            )
        )

    return projections


def _project_legacy_fan(
    device_payload: Mapping[str, Any], *, domain: str
) -> HAFanProjection | None:
    """兼容旧版扁平载荷格式的风扇投影。"""
    if to_str(device_payload.get("type")) != "fan":
        return None

    params = _params(device_payload)
    device_id = str(device_payload.get("device_id", "unknown"))
    speed_key = "lv" if "lv" in params else None
    mode_key = "m" if "m" in params else None
    direction_key = "dir" if "dir" in params else None
    speed_range = _fallback_speed_range(params)
    raw_mode = to_str(params.get("m"))
    preset_modes = [raw_mode] if raw_mode else None
    current_direction, direction_values = _fallback_direction_support(params)
    supported_features = _supported_features(
        power_key="p" if "p" in params else None,
        speed_key=speed_key,
        mode_key=mode_key,
        preset_modes=preset_modes,
        direction_key=direction_key,
        direction_values=direction_values,
    )

    return HAFanProjection(
        component_id="fan",
        unique_id=f"{domain}_{device_id}_fan",
        name=None,
        available=to_bool(device_payload.get("online"), default=False),
        is_on=_is_on(params, "p" if "p" in params else None, speed_key, mode_key),
        percentage=_project_percentage(params, speed_key, speed_range),
        speed_count=_speed_count(speed_range),
        preset_mode=to_str(params.get("m")),
        preset_modes=preset_modes,
        current_direction=current_direction,
        supported_features=supported_features,
        power_key="p" if "p" in params else None,
        speed_key=speed_key,
        mode_key=mode_key,
        direction_key=direction_key,
        speed_range=speed_range,
        direction_values=direction_values,
        device_info=project_payload_device_info(device_payload),
        icon="mdi:fan",
    )
