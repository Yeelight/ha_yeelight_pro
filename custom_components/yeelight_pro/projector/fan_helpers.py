"""Fan-specific helper functions for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.fan import FanEntityFeature

from ..canonical.models import ComponentInstanceModel, ComponentModel
from ..utils import to_bool, to_int, to_str
from .common import NumericRange, component_display_label, component_index
from .fan_value_helpers import (
    fan_speed_count,
    project_fan_percentage as _project_percentage,
    raw_prop as _raw_prop,
)
from .platform_evidence import component_has_fan_evidence


def _looks_like_fan_component(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None,
) -> bool:
    return component_has_fan_evidence(component, product_component)


def _power_key(state: Mapping[str, Any], product_component: ComponentModel | None) -> str | None:
    return _first_control_key(state, product_component, ("vmcp",))


def _speed_key(state: Mapping[str, Any], product_component: ComponentModel | None) -> str | None:
    return _first_control_key(state, product_component, ("vmcf",))


def _mode_key(state: Mapping[str, Any], product_component: ComponentModel | None) -> str | None:
    return None


def _direction_key(state: Mapping[str, Any], product_component: ComponentModel | None) -> str | None:
    return None


def _first_control_key(
    state: Mapping[str, Any],
    product_component: ComponentModel | None,
    candidates: tuple[str, ...],
) -> str | None:
    for candidate in candidates:
        if candidate in state or _product_prop(product_component, candidate) is not None:
            return candidate
    return None


def _resolve_control_key(
    component_id: str,
    prop_id: str | None,
    params: Mapping[str, Any],
    *,
    key_map: Mapping[str, Mapping[str, str]] | None = None,
) -> str | None:
    if prop_id is None:
        return None

    mapped = (key_map or {}).get(component_id, {}).get(prop_id)
    if mapped:
        return mapped

    index = component_index(component_id)
    if index is not None:
        candidate = f"{index}-{prop_id}"
        if candidate in params:
            return candidate
    return prop_id


def _speed_range(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None,
    state: Mapping[str, Any],
) -> NumericRange | None:
    raw_constraint = None
    if component.instance_capabilities is not None:
        raw_constraint = component.instance_capabilities.constraints.get("speed_level")
        if not isinstance(raw_constraint, Mapping):
            raw_constraint = component.instance_capabilities.constraints.get("speed")

    if isinstance(raw_constraint, Mapping):
        resolved = _range_from_mapping(raw_constraint)
        if resolved is not None:
            return resolved

    prop = (
        _product_prop(product_component, "vmcf")
    )
    if prop is not None and prop.value_range is not None:
        return NumericRange(
            min=to_int(prop.value_range.min),
            max=to_int(prop.value_range.max),
            step=to_int(prop.value_range.step),
        )

    return _fallback_speed_range(state)


def _fallback_speed_range(state: Mapping[str, Any]) -> NumericRange | None:
    raw_speed = to_int(state.get("vmcf"))
    if raw_speed is None:
        return None
    if 0 <= raw_speed <= 100:
        return NumericRange(min=1, max=100, step=1)
    return None


def _preset_modes(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None,
    state: Mapping[str, Any],
) -> list[str] | None:
    return None


def _direction_support(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None,
    state: Mapping[str, Any],
) -> tuple[str | None, dict[str, Any]]:
    return None, {}


def _supported_features(
    *,
    power_key: str | None,
    speed_key: str | None,
    mode_key: str | None,
    preset_modes: list[str] | None,
    direction_key: str | None,
    direction_values: Mapping[str, Any],
) -> FanEntityFeature:
    features = FanEntityFeature(0)
    if speed_key is not None:
        features |= FanEntityFeature.SET_SPEED
    if mode_key is not None and preset_modes:
        features |= FanEntityFeature.PRESET_MODE
    if direction_key is not None and direction_values:
        features |= FanEntityFeature.DIRECTION
    return features


def _is_on(
    state: Mapping[str, Any],
    power_key: str | None,
    speed_key: str | None,
    mode_key: str | None,
) -> bool:
    if power_key is not None:
        raw_key = _raw_prop(power_key)
        if raw_key is None:
            return False
        return to_bool(state.get(raw_key), default=False)

    percentage = _project_percentage(state, speed_key, None)
    if percentage is not None and percentage > 0:
        return True

    return _state_text(state, mode_key) is not None


def _speed_count(speed_range: NumericRange | None) -> int:
    """兼容 fan.py 旧私有导入路径的风速档位计数入口."""
    return fan_speed_count(speed_range)


def _state_text(state: Mapping[str, Any], prop_key: str | None) -> str | None:
    raw_key = _raw_prop(prop_key)
    if raw_key is None:
        return None
    return to_str(state.get(raw_key))


def _product_prop(product_component: ComponentModel | None, prop_id: str):
    if product_component is None:
        return None
    return next((prop for prop in product_component.properties if prop.prop_id == prop_id), None)


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _range_from_mapping(payload: Mapping[str, Any]) -> NumericRange | None:
    minimum = to_int(payload.get("min"))
    maximum = to_int(payload.get("max"))
    step = to_int(payload.get("step"))
    if minimum is None and maximum is None and step is None:
        return None
    return NumericRange(min=minimum, max=maximum, step=step)


def _project_fan_name(component: ComponentInstanceModel) -> str | None:
    lowered = component.component_id.lower()
    if lowered == "fresh_air":
        return "新风"
    return component_display_label(component)
