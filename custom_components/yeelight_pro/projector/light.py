"""Yeelight Pro 灯光投影模块.

将设备运行时数据投影为 Home Assistant 灯光实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.components.light import ColorMode

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..core.device_runtime_capabilities import state_blocks_light_projection
from ..utils import matches_category, to_bool, to_category
from .common import (
    NumericRange,
    component_index,
    load_instance,
    load_product_model,
    payload_available,
    product_component,
    schema_backed_component_available,
)
from .device import project_payload_device_info
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
    _state_has_light_property,
)

LIGHT_COLOR_MODE_HINT_KEY = _LIGHT_COLOR_MODE_HINT_KEY
NON_LIGHT_COMPONENT_TOKENS = ("sensor", "motion", "presence", "occupancy", "contact", "battery")


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
    power_key: str = "p"
    brightness_key: str = "l"
    color_temp_key: str = "ct"
    rgb_key: str = "c"


def project_light(device_payload: Mapping[str, Any], *, domain: str) -> HALightProjection | None:
    """将协调器设备载荷投影为 Home Assistant 灯光视图。"""
    lights = project_lights(device_payload, domain=domain)
    return lights[0] if lights else None


def project_lights(device_payload: Mapping[str, Any], *, domain: str) -> list[HALightProjection]:
    """将协调器设备载荷投影为一个或多个 Home Assistant 灯光视图。"""
    instance = load_instance(device_payload)
    if instance is None:
        legacy = _project_legacy_light(device_payload, domain=domain)
        return [legacy] if legacy is not None else []

    components = _light_components(instance, device_payload)
    total = len(components)
    return [
        _project_instance_light(
            device_payload,
            instance,
            component,
            total=total,
            domain=domain,
        )
        for component in components
    ]


def _project_legacy_light(
    device_payload: Mapping[str, Any], *, domain: str
) -> HALightProjection | None:
    """兼容旧版扁平载荷格式的灯光投影。"""
    state = dict(device_payload.get("params") or {})
    if not _payload_can_project_light(device_payload, state):
        return None

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
    is_on = to_bool(state.get("p"))
    device_id = str(device_payload.get("device_id", "unknown"))

    return HALightProjection(
        component_id="light",
        unique_id=f"{domain}_{device_id}_light",
        name=None,
        available=to_bool(device_payload.get("online"), default=True),
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
        device_info=project_payload_device_info(device_payload),
        icon=_project_icon(device_payload, supported_color_modes),
    )


def _project_instance_light(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    *,
    total: int,
    domain: str,
) -> HALightProjection:
    """投影单个 canonical light component。"""
    product_model = load_product_model(device_payload)
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
    is_on = to_bool(state.get("p"))

    return HALightProjection(
        component_id=component.component_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}",
        name=_project_light_name(component, total=total),
        available=schema_backed_component_available(
            payload_available(device_payload, instance),
            component,
            schema_component=product,
        ),
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
        device_info=project_payload_device_info(device_payload, instance),
        icon=_project_icon(device_payload, supported_color_modes),
        power_key=_component_control_key(component, "p"),
        brightness_key=_component_control_key(component, "l"),
        color_temp_key=_component_control_key(component, "ct"),
        rgb_key=_component_control_key(component, "c"),
    )


def _light_components(
    instance: HADeviceInstanceModel,
    device_payload: Mapping[str, Any],
) -> list[ComponentInstanceModel]:
    """返回所有应投影为 light 的组件，按原始组件顺序稳定排序。"""
    product_model = load_product_model(device_payload)
    components: list[ComponentInstanceModel] = []
    for component in instance.components:
        if _light_component_score(component, device_payload, product_model) > 0:
            components.append(component)

    if components:
        return components
    if _instance_can_fallback_to_light(device_payload, instance):
        return [instance.components[0]]
    return []


def _select_light_component(
    instance: HADeviceInstanceModel,
    device_payload: Mapping[str, Any],
) -> ComponentInstanceModel | None:
    """从设备实例中选择最佳灯光组件，基于类别和特征评分。"""
    product_model = load_product_model(device_payload)
    scored: list[tuple[int, int, ComponentInstanceModel]] = []

    for index, component in enumerate(instance.components):
        score = _light_component_score(component, device_payload, product_model)
        if score > 0:
            scored.append((score, -index, component))

    if scored:
        scored.sort(reverse=True, key=lambda item: (item[0], item[1]))
        return scored[0][2]

    if _instance_can_fallback_to_light(device_payload, instance):
        return instance.components[0]

    return None


def _light_component_score(
    component: ComponentInstanceModel,
    device_payload: Mapping[str, Any],
    product_model: Any | None,
) -> int:
    """根据类别、component_id 和能力判断组件是否属于 light。"""
    state = component.state
    product = product_component(product_model, component.component_id)
    features = _resolve_light_features(
        component,
        device_payload,
        product,
    )
    category = to_category(component.category)
    if not matches_category(category, LIGHT_CATEGORY_TOKENS):
        if matches_category(category, SWITCH_CATEGORY_TOKENS):
            return 0
        if not _payload_can_project_light(device_payload, state):
            return 0
    if not features and state_blocks_light_projection(device_payload, state):
        return 0
    if not features and not _state_has_light_property(state):
        return 0
    score = 0
    component_id = component.component_id.lower()

    if matches_category(category, LIGHT_CATEGORY_TOKENS):
        score += 200
    elif matches_category(category, SWITCH_CATEGORY_TOKENS):
        return 0

    if any(token in category for token in NON_LIGHT_COMPONENT_TOKENS):
        return 0
    if any(token in component_id for token in NON_LIGHT_COMPONENT_TOKENS):
        return 0

    if "light" in component_id:
        score += 100
    if any(key in state for key in ("l", "ct", "c")):
        score += 60
    if {"brightness", "color_temp", "rgb"} & features:
        score += 40
    if "p" in state and (score > 0 or _payload_can_project_light(device_payload, state)):
        score += 10
    return score


def _instance_can_fallback_to_light(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
) -> bool:
    """Return true only for payloads that are still plausibly lights."""
    if not instance.components:
        return False
    return _payload_can_project_light(device_payload, instance.components[0].state)


def _payload_can_project_light(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Avoid projecting broad cloud ``type=light`` rows as real lights."""
    if state_blocks_light_projection(device_payload, state):
        return False
    if not {"p", "l", "ct", "c"} & set(state):
        return False

    category = to_category(device_payload.get("iot_category") or device_payload.get("category"))
    if category == "light" or matches_category(category, LIGHT_CATEGORY_TOKENS):
        return True

    return _legacy_type_light_has_controls(device_payload, state)


def _legacy_type_light_has_controls(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Keep old light rows only when their state exposes real light controls."""
    if to_category(device_payload.get("type")) != "light":
        return False
    if to_category(device_payload.get("category")):
        return False
    return bool({"l", "ct", "c"} & set(state))


def _component_control_key(component: ComponentInstanceModel, prop: str) -> str:
    """返回组件控制键；带 index 的 OpenAPI 子设备使用 N-prop。"""
    index = component_index(component.component_id)
    if index is None:
        return prop
    return f"{index}-{prop}"


__all__ = ["HALightProjection", "LIGHT_COLOR_MODE_HINT_KEY", "project_light", "project_lights"]
