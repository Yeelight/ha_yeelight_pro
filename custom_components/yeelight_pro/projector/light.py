"""Yeelight Pro 灯光投影模块.

将设备运行时数据投影为 Home Assistant 灯光实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.components.light import ColorMode

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..utils import matches_category, to_bool, to_category
from .common import NumericRange, load_instance, load_product_model, product_component
from .device import project_device_info
from .light_helpers import (
    DEFAULT_BRIGHTNESS_RANGE,
    DEFAULT_COLOR_TEMP_RANGE_KELVIN,
    LIGHT_CATEGORY_TOKENS,
    LIGHT_COLOR_MODE_HINT_KEY as _LIGHT_COLOR_MODE_HINT_KEY,
    SWITCH_CATEGORY_TOKENS,
    _constraint,
    _has_brightness_capability,
    _has_color_temp_capability,
    _infer_features_from_payload,
    _project_brightness,
    _project_color_temp,
    _project_icon,
    _project_light_name,
    _project_max_mireds,
    _project_min_mireds,
    _project_rgb_color,
    _resolve_color_mode,
    _resolve_light_features,
    _resolve_range,
    _resolve_supported_color_modes,
)

LIGHT_COLOR_MODE_HINT_KEY = _LIGHT_COLOR_MODE_HINT_KEY


@dataclass(slots=True)
class HALightProjection:
    """设备运行时数据投影后的 Home Assistant 灯光视图。"""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    is_on: bool
    brightness: int | None
    color_temp: int | None
    rgb_color: tuple[int, int, int] | None
    supported_color_modes: set[ColorMode]
    color_mode: ColorMode
    min_mireds: int | None
    max_mireds: int | None
    brightness_range: NumericRange | None
    color_temp_range_kelvin: NumericRange | None
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_light(device_payload: Mapping[str, Any], *, domain: str) -> HALightProjection | None:
    """将协调器设备载荷投影为 Home Assistant 灯光视图。"""
    instance = load_instance(device_payload)
    if instance is None:
        return _project_legacy_light(device_payload, domain=domain)

    product_model = load_product_model(device_payload)
    component = _select_light_component(instance, device_payload)
    if component is None:
        return None

    state = dict(component.state)
    product = product_component(product_model, component.component_id)
    features = _resolve_light_features(component, device_payload, product)
    supported_color_modes = _resolve_supported_color_modes(features)
    color_mode = _resolve_color_mode(
        supported_color_modes,
        state=state,
        device_payload=device_payload,
    )
    brightness_range = _resolve_range(
        _constraint(component, "brightness", product),
        default=(
            DEFAULT_BRIGHTNESS_RANGE
            if _has_brightness_capability(features, state)
            else None
        ),
    )
    color_temp_range = _resolve_range(
        _constraint(component, "color_temp_kelvin", product),
        default=(
            DEFAULT_COLOR_TEMP_RANGE_KELVIN
            if _has_color_temp_capability(features, state)
            else None
        ),
    )
    is_on = to_bool(state.get("p", state.get("on")))

    return HALightProjection(
        component_id=component.component_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}",
        name=_project_light_name(component),
        available=bool(instance.online and component.available),
        is_on=is_on,
        brightness=_project_brightness(state, brightness_range, is_on=is_on),
        color_temp=_project_color_temp(state),
        rgb_color=_project_rgb_color(state),
        supported_color_modes=supported_color_modes,
        color_mode=color_mode,
        min_mireds=_project_min_mireds(color_temp_range),
        max_mireds=_project_max_mireds(color_temp_range),
        brightness_range=brightness_range,
        color_temp_range_kelvin=color_temp_range,
        device_info=project_device_info(instance),
        icon=_project_icon(device_payload, supported_color_modes),
    )


def _project_legacy_light(
    device_payload: Mapping[str, Any], *, domain: str
) -> HALightProjection | None:
    """兼容旧版扁平载荷格式的灯光投影。"""
    if device_payload.get("type") != "light":
        return None

    state = dict(device_payload.get("params") or {})
    features = _infer_features_from_payload(device_payload, state)
    supported_color_modes = _resolve_supported_color_modes(features)
    color_mode = _resolve_color_mode(
        supported_color_modes,
        state=state,
        device_payload=device_payload,
    )
    brightness_range = _resolve_range(
        None,
        default=(
            DEFAULT_BRIGHTNESS_RANGE
            if _has_brightness_capability(features, state)
            else None
        ),
    )
    color_temp_range = _resolve_range(
        None,
        default=(
            DEFAULT_COLOR_TEMP_RANGE_KELVIN
            if _has_color_temp_capability(features, state)
            else None
        ),
    )
    is_on = to_bool(state.get("p", state.get("on")))
    device_id = str(device_payload.get("device_id", "unknown"))

    return HALightProjection(
        component_id="light",
        unique_id=f"{domain}_{device_id}_light",
        name=None,
        available=to_bool(device_payload.get("online"), default=False),
        is_on=is_on,
        brightness=_project_brightness(state, brightness_range, is_on=is_on),
        color_temp=_project_color_temp(state),
        rgb_color=_project_rgb_color(state),
        supported_color_modes=supported_color_modes,
        color_mode=color_mode,
        min_mireds=_project_min_mireds(color_temp_range),
        max_mireds=_project_max_mireds(color_temp_range),
        brightness_range=brightness_range,
        color_temp_range_kelvin=color_temp_range,
        device_info=None,
        icon=_project_icon(device_payload, supported_color_modes),
    )


def _select_light_component(
    instance: HADeviceInstanceModel,
    device_payload: Mapping[str, Any],
) -> ComponentInstanceModel | None:
    """从设备实例中选择最佳灯光组件，基于类别和特征评分。"""
    product_model = load_product_model(device_payload)
    scored: list[tuple[int, int, ComponentInstanceModel]] = []

    for index, component in enumerate(instance.components):
        state = component.state
        features = _resolve_light_features(
            component,
            device_payload,
            product_component(product_model, component.component_id),
        )
        score = 0
        category = to_category(component.category)

        if matches_category(category, SWITCH_CATEGORY_TOKENS):
            continue
        if matches_category(category, LIGHT_CATEGORY_TOKENS):
            score += 200

        if "light" in component.component_id.lower():
            score += 100
        if any(key in state for key in ("l", "ct", "c")):
            score += 60
        if {"brightness", "color_temp", "rgb"} & features:
            score += 40

        if score > 0:
            scored.append((score, -index, component))

    if scored:
        scored.sort(reverse=True, key=lambda item: (item[0], item[1]))
        return scored[0][2]

    if device_payload.get("type") == "light" and instance.components:
        return instance.components[0]

    return None
