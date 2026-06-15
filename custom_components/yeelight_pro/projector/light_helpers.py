"""Light-specific helper functions for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.light import ColorMode

from ..canonical.models import ComponentInstanceModel, ComponentModel
from ..device_display import channel_name_label
from ..utils import to_category, to_int, to_str
from .common import NumericRange, component_index, humanize_component_id
from .platform_evidence import payload_category

DEFAULT_MIN_COLOR_TEMP_KELVIN = 2700
DEFAULT_MAX_COLOR_TEMP_KELVIN = 6500
DEFAULT_BRIGHTNESS_RANGE = (1, 100, 1)
DEFAULT_COLOR_TEMP_RANGE_KELVIN = (
    DEFAULT_MIN_COLOR_TEMP_KELVIN,
    DEFAULT_MAX_COLOR_TEMP_KELVIN,
    None,
)
LIGHT_COLOR_MODE_HINT_KEY = "light_color_mode"
LIGHT_COLOR_TEMP_MODE_TOKENS = {"color_temp", "colortemp", "ct", "temperature", "temp"}
LIGHT_RGB_MODE_TOKENS = {"rgb", "color", "colour"}
LEGACY_LIGHT_PRODUCT_TYPES = frozenset({2, 3, 4, 14, 30})


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
    features: set[str] = set()

    if "p" in state:
        features.add("onoff")
    if "l" in state:
        features.add("brightness")
    if "ct" in state:
        features.add("color_temp")
    if "c" in state:
        features.add("rgb")
    if not features and _payload_is_light(device_payload):
        features.update(_legacy_product_type_features(device_payload.get("product_type")))

    return features


def _payload_is_light(device_payload: Mapping[str, Any]) -> bool:
    """Return true when payload identity is explicitly light-like."""
    if to_category(device_payload.get("ha_platform")) == "light":
        return True
    return payload_category(device_payload) == "light"


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

    for mode in (ColorMode.COLOR_TEMP, ColorMode.BRIGHTNESS, ColorMode.RGB, ColorMode.ONOFF):
        if mode in supported_color_modes:
            return mode
    return ColorMode.ONOFF


def _project_brightness(
    state: Mapping[str, Any],
    brightness_range: NumericRange | None,
    *,
    is_on: bool,
) -> int | None:
    """将原始亮度值归一化为 HA 0-255 范围。"""
    raw = to_int(state.get("l"))
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
    kelvin = _project_color_temp_kelvin(state)
    if kelvin is None:
        return None
    return int(1000000 / kelvin)


def _project_color_temp_kelvin(state: Mapping[str, Any]) -> int | None:
    """返回原始开尔文色温，避免 mired 往返造成精度漂移。"""
    kelvin = to_int(state.get("ct"))
    if kelvin is None or kelvin <= 0:
        return None
    return kelvin


def _project_rgb_color(state: Mapping[str, Any]) -> tuple[int, int, int] | None:
    """将整数 RGB 值解码为 (r, g, b) 元组。"""
    color = to_int(state.get("c"))
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


def _state_has_light_property(state: Mapping[str, Any]) -> bool:
    """Return true when runtime state carries real light properties."""
    return bool({"p", "l", "ct", "c"} & set(state))


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


def _project_light_name(component: ComponentInstanceModel, *, total: int = 1) -> str | None:
    """从组件 ID 推断灯光显示名称。"""
    friendly_name = _friendly_component_name(component)
    if friendly_name and total > 1:
        return friendly_name

    index = component_index(component.component_id)
    if index is not None:
        return _indexed_channel_name(index, total=total)

    lowered = component.component_id.lower()
    if lowered in {"light", "main", "main_light"}:
        return None
    if lowered.startswith("light_"):
        suffix = lowered.removeprefix("light_").strip("_")
        if suffix.isdigit():
            return _indexed_channel_name(to_int(suffix), total=total)
        return humanize_component_id(suffix)
    if lowered.startswith("light"):
        suffix = lowered.removeprefix("light")
        if suffix.isdigit():
            return _indexed_channel_name(to_int(suffix), total=total)
        return None
    return humanize_component_id(component.component_id)


def _indexed_channel_name(index: int | None, *, total: int) -> str | None:
    """为多路灯光生成稳定的通道名，单路主实体交给设备名承载。"""
    if index is None or total <= 1:
        return None
    return channel_name_label(index=index, component={"io": "output"})


def _friendly_component_name(component: ComponentInstanceModel) -> str | None:
    """返回来自产品 schema 的组件友好名称，过滤技术占位名。"""
    for value in (getattr(component, "desc", None), getattr(component, "name", None)):
        text = to_str(value)
        if not text:
            continue
        friendly = text.removesuffix("组件").strip()
        if friendly and friendly.lower() not in {"light", "main", "main_light"}:
            return friendly
    return None


def _has_brightness_capability(features: set[str], state: Mapping[str, Any]) -> bool:
    """判断是否具有亮度控制能力。"""
    return "brightness" in features or "l" in state


def _has_color_temp_capability(features: set[str], state: Mapping[str, Any]) -> bool:
    """判断是否具有色温控制能力。"""
    return "color_temp" in features or "ct" in state


def _legacy_product_type_features(product_type: Any) -> set[str]:
    """仅在无 schema/state 能力时兼容旧 product_type 灯型提示。"""
    normalized = to_int(product_type)
    if normalized not in LEGACY_LIGHT_PRODUCT_TYPES:
        return set()
    features = {"onoff", "brightness"}
    if normalized == 3:
        features.add("color_temp")
    if normalized == 4:
        features.add("rgb")
    return features


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
    has_color_temp = to_int(state.get("ct")) is not None
    has_rgb = to_int(state.get("c")) is not None

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
