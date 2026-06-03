"""Yeelight Pro 灯光投影模块.

将设备运行时数据投影为 Home Assistant 灯光实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from homeassistant.components.light import ColorMode

from ..canonical.models import ComponentInstanceModel, ComponentModel, HADeviceInstanceModel, HAProductModel
from ..utils import to_bool, to_int, to_str, to_category, matches_category
from .device import project_device_info

DEFAULT_BRIGHTNESS_RANGE = (1, 100, 1)
DEFAULT_COLOR_TEMP_RANGE_KELVIN = (2700, 6500, None)
LIGHT_CATEGORY_TOKENS = ("light", "lamp", "灯", "灯带", "彩光", "色温")
SWITCH_CATEGORY_TOKENS = ("switch", "relay", "outlet", "开关", "面板")
LIGHT_COLOR_MODE_HINT_KEY = "light_color_mode"
LIGHT_COLOR_TEMP_MODE_TOKENS = {"color_temp", "colortemp", "ct", "temperature", "temp"}
LIGHT_RGB_MODE_TOKENS = {"rgb", "color", "colour"}
COMPONENT_INDEX_RE = re.compile(r"_(?P<index>\d+)$")


@dataclass(slots=True)
class NumericRange:
    """归一化的数值范围元数据。"""

    min: int | None = None
    max: int | None = None
    step: int | None = None


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
    instance = _load_instance(device_payload)
    if instance is None:
        return _project_legacy_light(device_payload, domain=domain)

    product_model = _load_product_model(device_payload)
    component = _select_light_component(instance, device_payload)
    if component is None:
        return None

    state = dict(component.state)
    product_component = _product_component(product_model, component.component_id)
    features = _resolve_light_features(component, device_payload, product_component)
    supported_color_modes = _resolve_supported_color_modes(features)
    color_mode = _resolve_color_mode(
        supported_color_modes,
        state=state,
        device_payload=device_payload,
    )
    brightness_range = _resolve_range(
        _constraint(component, "brightness", product_component),
        default=DEFAULT_BRIGHTNESS_RANGE if _has_brightness_capability(features, state) else None,
    )
    color_temp_range = _resolve_range(
        _constraint(component, "color_temp_kelvin", product_component),
        default=DEFAULT_COLOR_TEMP_RANGE_KELVIN if _has_color_temp_capability(features, state) else None,
    )

    return HALightProjection(
        component_id=component.component_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}",
        name=_project_light_name(component),
        available=bool(instance.online and component.available),
        is_on=to_bool(state.get("p", state.get("on"))),
        brightness=_project_brightness(
            state,
            brightness_range,
            is_on=to_bool(state.get("p", state.get("on"))),
        ),
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


def _load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从载荷中加载设备实例模型。"""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _load_product_model(device_payload: Mapping[str, Any]) -> HAProductModel | None:
    """从载荷中加载产品模型。"""
    payload = device_payload.get("ha_product_model")
    if not isinstance(payload, Mapping):
        return None
    return HAProductModel.from_dict(payload)


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
        default=DEFAULT_BRIGHTNESS_RANGE if _has_brightness_capability(features, state) else None,
    )
    color_temp_range = _resolve_range(
        None,
        default=DEFAULT_COLOR_TEMP_RANGE_KELVIN if _has_color_temp_capability(features, state) else None,
    )

    device_id = str(device_payload.get("device_id", "unknown"))
    return HALightProjection(
        component_id="light",
        unique_id=f"{domain}_{device_id}_light",
        name=None,
        available=to_bool(device_payload.get("online"), default=False),
        is_on=to_bool(state.get("p", state.get("on"))),
        brightness=_project_brightness(
            state,
            brightness_range,
            is_on=to_bool(state.get("p", state.get("on"))),
        ),
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
    product_model = _load_product_model(device_payload)
    scored: list[tuple[int, int, ComponentInstanceModel]] = []

    for index, component in enumerate(instance.components):
        state = component.state
        features = _resolve_light_features(
            component,
            device_payload,
            _product_component(product_model, component.component_id),
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


def _resolve_light_features(
    component: ComponentInstanceModel,
    device_payload: Mapping[str, Any],
    product_component: ComponentModel | None,
) -> set[str]:
    """解析组件的灯光特征集合，优先使用实例能力，回退到产品定义和载荷推断。"""
    features = {
        str(item).strip().lower()
        for item in (component.instance_capabilities.features if component.instance_capabilities else [])
        if str(item).strip()
    }
    if features:
        return features
    schema_features = _infer_features_from_product_component(product_component)
    if schema_features:
        return schema_features
    return _infer_features_from_payload(device_payload, component.state)


def _infer_features_from_payload(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> set[str]:
    """从载荷和状态中推断灯光特征。"""
    product_type = device_payload.get("product_type")
    features: set[str] = set()

    if "p" in state or "on" in state or device_payload.get("type") == "light":
        features.add("onoff")
    if "l" in state or product_type in {2, 3, 4, 14, 30}:
        features.add("brightness")
    if "ct" in state or product_type == 3:
        features.add("color_temp")
    if "c" in state or product_type == 4:
        features.add("rgb")

    return features


def _resolve_supported_color_modes(features: set[str]) -> set[ColorMode]:
    """根据特征集合解析支持的 HA 颜色模式。"""
    modes: set[ColorMode] = set()
    if "color_temp" in features:
        modes.add(ColorMode.COLOR_TEMP)
    if "rgb" in features:
        modes.add(ColorMode.RGB)
    if not modes and "brightness" in features:
        modes.add(ColorMode.BRIGHTNESS)
    if not modes:
        modes.add(ColorMode.ONOFF)
    return modes


def _resolve_color_mode(
    supported_color_modes: set[ColorMode],
    *,
    state: Mapping[str, Any],
    device_payload: Mapping[str, Any],
) -> ColorMode:
    """解析当前颜色模式：显式 > 提示 > 推断 > 优先级回退。"""
    explicit_mode = _explicit_light_color_mode(state)
    if explicit_mode in supported_color_modes:
        return explicit_mode

    hinted_mode = _hinted_light_color_mode(device_payload)
    if hinted_mode in supported_color_modes:
        return hinted_mode

    inferred_mode = _infer_light_color_mode_from_state(state)
    if inferred_mode in supported_color_modes:
        return inferred_mode

    for mode in (ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.BRIGHTNESS, ColorMode.ONOFF):
        if mode in supported_color_modes:
            return mode
    return ColorMode.ONOFF


def _project_brightness(
    state: Mapping[str, Any],
    brightness_range: NumericRange | None,
    *,
    is_on: bool,
) -> int | None:
    """将原始亮度值归一化为 HA 0-255 范围。

    使用线性映射：normalized = (raw - min) / (max - min) * 255。
    设备开启且投影值为 0 时，钳制为 1（HA 约定）。
    """
    raw = to_int(state.get("l", state.get("brightness")))
    if raw is None:
        return None

    minimum = brightness_range.min if brightness_range and brightness_range.min is not None else 1
    maximum = brightness_range.max if brightness_range and brightness_range.max is not None else 100
    if maximum <= minimum:
        projected = max(0, min(255, raw))
        return max(1, projected) if is_on and projected == 0 else projected

    normalized = (raw - minimum) / (maximum - minimum)
    normalized = max(0.0, min(1.0, normalized))
    projected = int(round(normalized * 255))
    return max(1, projected) if is_on and projected == 0 else projected


def _project_color_temp(state: Mapping[str, Any]) -> int | None:
    """将开尔文色温转换为 HA mired 单位。"""
    kelvin = to_int(state.get("ct", state.get("color_temp_kelvin")))
    if kelvin is None or kelvin <= 0:
        return None
    return int(1000000 / kelvin)


def _project_rgb_color(state: Mapping[str, Any]) -> tuple[int, int, int] | None:
    """将整数 RGB 值解码为 (r, g, b) 元组。"""
    color = to_int(state.get("c", state.get("rgb")))
    if color is None:
        return None
    return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)


def _project_min_mireds(color_temp_range: NumericRange | None) -> int | None:
    """从色温范围的最大开尔文值计算最小 mired 值。"""
    if color_temp_range is None or color_temp_range.max is None or color_temp_range.max <= 0:
        return None
    return int(1000000 / color_temp_range.max)


def _project_max_mireds(color_temp_range: NumericRange | None) -> int | None:
    """从色温范围的最小开尔文值计算最大 mired 值。"""
    if color_temp_range is None or color_temp_range.min is None or color_temp_range.min <= 0:
        return None
    return int(1000000 / color_temp_range.min)


def _resolve_range(
    payload: Any,
    *,
    default: tuple[int | None, int | None, int | None] | None,
) -> NumericRange | None:
    """从载荷或默认值解析数值范围。"""
    if isinstance(payload, Mapping):
        return NumericRange(
            min=to_int(payload.get("min")),
            max=to_int(payload.get("max")),
            step=to_int(payload.get("step")),
        )
    if default is None:
        return None
    return NumericRange(min=default[0], max=default[1], step=default[2])


def _constraint(
    component: ComponentInstanceModel,
    key: str,
    product_component: ComponentModel | None,
) -> Mapping[str, Any] | None:
    """获取组件约束：优先实例能力，回退产品定义。"""
    if component.instance_capabilities is None:
        return _product_constraint(product_component, key)
    value = component.instance_capabilities.constraints.get(key)
    if isinstance(value, Mapping):
        return value
    return _product_constraint(product_component, key)


def _product_component(
    product_model: HAProductModel | None,
    component_id: str,
) -> ComponentModel | None:
    """从产品模型中查找匹配的组件定义。"""
    if product_model is None:
        return None
    return next(
        (item for item in product_model.components if item.component_id == component_id),
        None,
    )


def _infer_features_from_product_component(product_component: ComponentModel | None) -> set[str]:
    """从产品组件属性定义中推断灯光特征。"""
    if product_component is None:
        return set()

    prop_ids = {prop.prop_id for prop in product_component.properties}
    features: set[str] = set()
    if "p" in prop_ids or "sp" in prop_ids:
        features.add("onoff")
    if "l" in prop_ids:
        features.add("brightness")
    if "ct" in prop_ids:
        features.add("color_temp")
    if "c" in prop_ids:
        features.add("rgb")
    return features


def _product_constraint(
    product_component: ComponentModel | None,
    key: str,
) -> Mapping[str, Any] | None:
    """从产品组件属性中提取数值约束。"""
    if product_component is None:
        return None

    prop_id = None
    if key == "brightness":
        prop_id = "l"
    elif key == "color_temp_kelvin":
        prop_id = "ct"

    if prop_id is None:
        return None

    for prop in product_component.properties:
        if prop.prop_id != prop_id or prop.value_range is None:
            continue
        return {
            "min": prop.value_range.min,
            "max": prop.value_range.max,
            "step": prop.value_range.step,
        }
    return None


def _project_icon(
    device_payload: Mapping[str, Any],
    supported_color_modes: set[ColorMode],
) -> str | None:
    """根据产品类型和颜色模式选择合适的 MDI 图标。"""
    product_type = device_payload.get("product_type", 1)
    icon_map = {
        1: "mdi:lightbulb",
        2: "mdi:lightbulb-outline",
        3: "mdi:lightbulb-on",
        4: "mdi:lightbulb-multiple",
        14: "mdi:spotlight",
        30: "mdi:ceiling-light",
    }
    icon = icon_map.get(product_type)
    if icon:
        return icon
    if ColorMode.RGB in supported_color_modes:
        return "mdi:lightbulb-multiple"
    if ColorMode.COLOR_TEMP in supported_color_modes:
        return "mdi:lightbulb-on"
    return "mdi:lightbulb"


def _project_light_name(component: ComponentInstanceModel) -> str | None:
    """从组件 ID 推断灯光显示名称。"""
    index = _component_index(component.component_id)
    if index is not None:
        return str(index)

    lowered = component.component_id.lower()
    if lowered in {"light", "main", "main_light"}:
        return None
    if lowered.startswith("light_"):
        return lowered.removeprefix("light_").replace("_", " ").strip() or None
    if lowered.startswith("light"):
        return None
    return _humanize_component_id(component.component_id)


def _has_brightness_capability(features: set[str], state: Mapping[str, Any]) -> bool:
    """判断是否具有亮度控制能力。"""
    return "brightness" in features or "l" in state


def _has_color_temp_capability(features: set[str], state: Mapping[str, Any]) -> bool:
    """判断是否具有色温控制能力。"""
    return "color_temp" in features or "ct" in state


def _hinted_light_color_mode(device_payload: Mapping[str, Any]) -> ColorMode | None:
    """从运行时提示中解析颜色模式。"""
    runtime_hints = device_payload.get("runtime_hints")
    if not isinstance(runtime_hints, Mapping):
        return None
    return _parse_light_color_mode(runtime_hints.get(LIGHT_COLOR_MODE_HINT_KEY))


def _explicit_light_color_mode(state: Mapping[str, Any]) -> ColorMode | None:
    """从状态中读取显式颜色模式。"""
    for key in ("color_mode", "colorMode", "mode", "m"):
        parsed = _parse_light_color_mode(state.get(key))
        if parsed is not None:
            return parsed
    return None


def _infer_light_color_mode_from_state(state: Mapping[str, Any]) -> ColorMode | None:
    """根据状态键的存在推断颜色模式。"""
    has_color_temp = to_int(state.get("ct", state.get("color_temp_kelvin"))) is not None
    has_rgb = to_int(state.get("c", state.get("rgb"))) is not None

    if has_rgb and not has_color_temp:
        return ColorMode.RGB
    if has_color_temp and not has_rgb:
        return ColorMode.COLOR_TEMP
    return None


def _parse_light_color_mode(value: Any) -> ColorMode | None:
    """将字符串值解析为 HA ColorMode 枚举。"""
    text = to_str(value)
    if not text:
        return None

    normalized = text.lower().replace("-", "_").replace(" ", "_")
    if normalized in LIGHT_RGB_MODE_TOKENS:
        return ColorMode.RGB
    if normalized in LIGHT_COLOR_TEMP_MODE_TOKENS:
        return ColorMode.COLOR_TEMP
    return None


def _component_index(component_id: str) -> int | None:
    """从组件 ID 中提取数字索引。"""
    match = COMPONENT_INDEX_RE.search(component_id)
    if not match:
        return None
    return to_int(match.group("index"))


def _humanize_component_id(component_id: str) -> str | None:
    """将组件 ID 转换为人类可读名称。"""
    text = component_id.replace("_", " ").strip()
    return text or None
