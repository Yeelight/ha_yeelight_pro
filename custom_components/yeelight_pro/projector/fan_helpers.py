"""Fan-specific helper functions for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.fan import DIRECTION_FORWARD, DIRECTION_REVERSE, FanEntityFeature

from ..canonical.models import ComponentInstanceModel, ComponentModel
from ..device_display import channel_name_label
from ..utils import matches_category, to_bool, to_category, to_int, to_str
from .common import NumericRange, component_index, humanize_component_id
from .fan_value_helpers import (
    direction_values_from_constraint as _direction_values_from_constraint,
    direction_values_from_value_list as _direction_values_from_value_list,
    enum_codes as _enum_codes,
    fan_speed_count,
    project_fan_percentage as _project_percentage,
    raw_prop as _raw_prop,
    to_ha_direction as _to_ha_direction,
)

FAN_CATEGORY_TOKENS = ("fan", "ceiling fan", "fresh air", "风扇", "吊扇", "新风")
LIGHT_CATEGORY_TOKENS = ("light", "lamp", "灯", "灯带", "彩光", "色温")


def _looks_like_fan_component(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None,
) -> bool:
    category = to_category(component.category or getattr(product_component, "category", None))
    lowered = component.component_id.lower()
    if matches_category(category, FAN_CATEGORY_TOKENS):
        return True
    if matches_category(category, LIGHT_CATEGORY_TOKENS):
        return False
    if "fan" in lowered or "风扇" in lowered or "吊扇" in lowered:
        return True

    features = {
        str(item).strip().lower()
        for item in (
            component.instance_capabilities.features
            if component.instance_capabilities is not None
            else []
        )
        if str(item).strip()
    }
    if {"speed", "direction", "mode"} & features:
        return True

    prop_ids = set(component.state.keys())
    if product_component is not None:
        prop_ids.update(prop.prop_id for prop in product_component.properties)
    return bool({"vmcp", "vmcf", "lv", "dir"} & {str(item) for item in prop_ids})


def _power_key(state: Mapping[str, Any], product_component: ComponentModel | None) -> str | None:
    return _first_control_key(state, product_component, ("vmcp", "p", "on"))


def _speed_key(state: Mapping[str, Any], product_component: ComponentModel | None) -> str | None:
    return _first_control_key(state, product_component, ("vmcf", "lv", "speed", "percentage"))


def _mode_key(state: Mapping[str, Any], product_component: ComponentModel | None) -> str | None:
    return _first_control_key(state, product_component, ("m", "mode"))


def _direction_key(state: Mapping[str, Any], product_component: ComponentModel | None) -> str | None:
    return _first_control_key(state, product_component, ("dir", "direction"))


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
        or _product_prop(product_component, "lv")
        or _product_prop(product_component, "speed")
    )
    if prop is not None and prop.value_range is not None:
        return NumericRange(
            min=to_int(prop.value_range.min),
            max=to_int(prop.value_range.max),
            step=to_int(prop.value_range.step),
        )

    return _fallback_speed_range(state)


def _fallback_speed_range(state: Mapping[str, Any]) -> NumericRange | None:
    raw_speed = to_int(
        state.get("vmcf", state.get("lv", state.get("speed", state.get("percentage"))))
    )
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
    raw_modes: list[str] = []
    if component.instance_capabilities is not None:
        constraints = component.instance_capabilities.constraints
        for key in ("mode", "preset_modes", "presetModes"):
            value = constraints.get(key)
            raw_modes.extend(_enum_codes(value))

    prop = _product_prop(product_component, "m") or _product_prop(product_component, "mode")
    if prop is not None:
        raw_modes.extend(item.code for item in prop.value_list if item.code)

    modes = []
    for mode in raw_modes:
        text = to_str(mode)
        if text and text not in modes:
            modes.append(text)

    current = to_str(state.get("m", state.get("mode")))
    if not modes and current:
        modes.append(current)

    return modes or None


def _direction_support(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None,
    state: Mapping[str, Any],
) -> tuple[str | None, dict[str, Any]]:
    direction_values: dict[str, Any] = {}

    if component.instance_capabilities is not None:
        constraints = component.instance_capabilities.constraints
        for key in ("direction", "dir"):
            value = constraints.get(key)
            direction_values.update(_direction_values_from_constraint(value))

    prop = _product_prop(product_component, "dir") or _product_prop(product_component, "direction")
    if prop is not None:
        direction_values.update(_direction_values_from_value_list(prop.value_list))

    current_direction = _to_ha_direction(state.get("dir", state.get("direction")), direction_values)

    if not direction_values and current_direction is not None:
        direction_values = {
            DIRECTION_FORWARD: DIRECTION_FORWARD,
            DIRECTION_REVERSE: DIRECTION_REVERSE,
        }

    return current_direction, direction_values


def _fallback_direction_support(state: Mapping[str, Any]) -> tuple[str | None, dict[str, Any]]:
    current_direction = _to_ha_direction(state.get("dir"), {})
    if current_direction is None:
        return None, {}
    return current_direction, {
        DIRECTION_FORWARD: DIRECTION_FORWARD,
        DIRECTION_REVERSE: DIRECTION_REVERSE,
    }


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
    index = component_index(component.component_id)
    if index is not None:
        return channel_name_label(index=index, component=component)

    lowered = component.component_id.lower()
    if lowered in {"fan", "main_fan", "fan_main"}:
        return None
    if text := to_str(component.name):
        return text
    if lowered.startswith("fan_"):
        text = lowered.removeprefix("fan_").replace("_", " ").strip()
        return text or None
    return humanize_component_id(component.component_id)
