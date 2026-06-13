"""Climate projector shared builder helpers."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.climate import ClimateEntityFeature

from .climate_helpers import (
    climate_fan_mode,
    climate_fan_mode_values,
    climate_fan_modes,
    climate_hvac_mode,
    climate_hvac_modes,
    state_key,
    state_value,
)
from ..utils import to_float


def build_climate_projection(
    projection_cls: type[Any],
    *,
    component_id: str,
    unique_id: str,
    name: str | None,
    available: bool,
    state: Mapping[str, Any],
    power_key: str | None,
    target_temperature_key: str | None,
    mode_key: str | None,
    fan_mode_key: str | None,
    current_temperature_key: str | None,
    schema_component: Any | None,
    device_info: dict[str, Any] | None,
) -> Any:
    """根据运行时状态构造 Home Assistant climate projection."""
    supported_features = ClimateEntityFeature(0)
    if target_temperature_key is not None:
        supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
    if fan_mode_key is not None:
        supported_features |= ClimateEntityFeature.FAN_MODE

    return projection_cls(
        component_id=component_id,
        unique_id=unique_id,
        name=name,
        available=available,
        current_temperature=(
            to_float(state_value(state, current_temperature_key))
            if state_key(current_temperature_key)
            else None
        ),
        target_temperature=(
            to_float(state_value(state, target_temperature_key))
            if state_key(target_temperature_key)
            else None
        ),
        hvac_mode=climate_hvac_mode(state, power_key=power_key, mode_key=mode_key),
        hvac_modes=climate_hvac_modes(mode_key),
        supported_features=supported_features,
        power_key=power_key,
        target_temperature_key=target_temperature_key,
        mode_key=mode_key,
        fan_mode_key=fan_mode_key,
        fan_mode=climate_fan_mode(state, fan_mode_key),
        fan_modes=climate_fan_modes(schema_component, fan_key=fan_mode_key),
        fan_mode_values=(
            climate_fan_mode_values(schema_component)
            if fan_mode_key is not None
            else {}
        ),
        device_info=device_info,
        icon="mdi:air-conditioner",
    )


__all__ = ["build_climate_projection"]
