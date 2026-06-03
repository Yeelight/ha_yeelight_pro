"""Yeelight Pro 风扇投影模块.

将设备运行时数据投影为 Home Assistant 风扇实体视图。
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntityFeature,
)
from homeassistant.util.percentage import ranged_value_to_percentage

from ..canonical.models import ComponentInstanceModel, ComponentModel, HADeviceInstanceModel, HAProductModel
from ..utils import to_bool, to_int, to_str, to_category, matches_category
from .device import project_device_info

FAN_CATEGORY_TOKENS = ("fan", "ceiling fan", "风扇", "吊扇")
LIGHT_CATEGORY_TOKENS = ("light", "lamp", "灯", "灯带", "彩光", "色温")
COMPONENT_INDEX_RE = re.compile(r"_(?P<index>\d+)$")


@dataclass(slots=True)
class NumericRange:
    """归一化的数值范围元数据。"""

    min: int | None = None
    max: int | None = None
    step: int | None = None


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
    device_info = project_device_info(instance)
    projections: list[HAFanProjection] = []

    for component in instance.components:
        product_component = _product_component(product_model, component.component_id)
        if not _looks_like_fan_component(component, product_component):
            continue

        state = dict(component.state)
        power_key = _resolve_control_key(component.component_id, _power_key(state, product_component), params)
        speed_key = _resolve_control_key(component.component_id, _speed_key(state, product_component), params)
        mode_key = _resolve_control_key(component.component_id, _mode_key(state, product_component), params)
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
                preset_mode=to_str(state.get(_raw_prop(mode_key))),
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
    preset_modes = [to_str(params["m"])] if to_str(params.get("m")) else None
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
        device_info=None,
        icon="mdi:fan",
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


def _looks_like_fan_component(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None,
) -> bool:
    """判断组件是否为风扇组件，基于类别、特征和属性。"""
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
    return bool({"lv", "dir"} & {str(item) for item in prop_ids})


def _power_key(
    state: Mapping[str, Any],
    product_component: ComponentModel | None,
) -> str | None:
    """解析电源控制键。"""
    for candidate in ("p", "on"):
        if candidate in state or _product_prop(product_component, candidate) is not None:
            return candidate
    return None


def _speed_key(
    state: Mapping[str, Any],
    product_component: ComponentModel | None,
) -> str | None:
    """解析速度控制键。"""
    for candidate in ("lv", "speed", "percentage"):
        if candidate in state or _product_prop(product_component, candidate) is not None:
            return candidate
    return None


def _mode_key(
    state: Mapping[str, Any],
    product_component: ComponentModel | None,
) -> str | None:
    """解析模式控制键。"""
    for candidate in ("m", "mode"):
        if candidate in state or _product_prop(product_component, candidate) is not None:
            return candidate
    return None


def _direction_key(
    state: Mapping[str, Any],
    product_component: ComponentModel | None,
) -> str | None:
    """解析方向控制键。"""
    for candidate in ("dir", "direction"):
        if candidate in state or _product_prop(product_component, candidate) is not None:
            return candidate
    return None


def _resolve_control_key(
    component_id: str,
    prop_id: str | None,
    params: Mapping[str, Any],
) -> str | None:
    """解析带组件索引前缀的控制键。"""
    if prop_id is None:
        return None

    index = _component_index(component_id)
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
    """解析速度范围，优先实例约束，回退产品定义，最后回退推断。"""
    raw_constraint = None
    if component.instance_capabilities is not None:
        raw_constraint = component.instance_capabilities.constraints.get("speed_level")
        if not isinstance(raw_constraint, Mapping):
            raw_constraint = component.instance_capabilities.constraints.get("speed")

    if isinstance(raw_constraint, Mapping):
        resolved = _range_from_mapping(raw_constraint)
        if resolved is not None:
            return resolved

    prop = _product_prop(product_component, "lv") or _product_prop(product_component, "speed")
    if prop is not None and prop.value_range is not None:
        return NumericRange(
            min=to_int(prop.value_range.min),
            max=to_int(prop.value_range.max),
            step=to_int(prop.value_range.step),
        )

    return _fallback_speed_range(state)


def _fallback_speed_range(state: Mapping[str, Any]) -> NumericRange | None:
    """从状态推断速度范围。"""
    raw_speed = to_int(state.get("lv", state.get("speed", state.get("percentage"))))
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
    """解析预设模式列表，优先实例约束，回退产品定义。"""
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
    """解析方向支持，包含当前方向和可选方向值映射。"""
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
    """回退方向支持推断。"""
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
    """根据可用控制键计算支持的功能标志。"""
    features = FanEntityFeature(0)
    if power_key is not None or speed_key is not None or mode_key is not None:
        features |= FanEntityFeature.TURN_ON
    if power_key is not None or speed_key is not None:
        features |= FanEntityFeature.TURN_OFF
    if speed_key is not None:
        features |= FanEntityFeature.SET_SPEED
    if mode_key is not None and preset_modes:
        features |= FanEntityFeature.PRESET_MODE
    if direction_key is not None and direction_values:
        features |= FanEntityFeature.DIRECTION
    return features


def _project_percentage(
    state: Mapping[str, Any],
    speed_key: str | None,
    speed_range: NumericRange | None,
) -> int | None:
    """将原始速度值归一化为 HA 百分比。"""
    if speed_key is None:
        return None

    raw = to_int(state.get(_raw_prop(speed_key)))
    if raw is None:
        return None

    if speed_range is None:
        return max(0, min(100, raw))

    minimum = speed_range.min if speed_range.min is not None else 1
    maximum = speed_range.max if speed_range.max is not None else 100
    if maximum < minimum:
        return max(0, min(100, raw))
    if minimum == 0 and raw == 0:
        return 0
    if raw <= 0:
        return 0
    return int(round(ranged_value_to_percentage((minimum, maximum), raw)))


def _is_on(
    state: Mapping[str, Any],
    power_key: str | None,
    speed_key: str | None,
    mode_key: str | None,
) -> bool:
    """判断风扇是否开启。"""
    if power_key is not None:
        raw_key = _raw_prop(power_key)
        return to_bool(state.get(raw_key), default=False)

    percentage = _project_percentage(state, speed_key, None)
    if percentage is not None and percentage > 0:
        return True

    return to_str(state.get(_raw_prop(mode_key))) is not None


def _speed_count(speed_range: NumericRange | None) -> int:
    """计算速度档位数。"""
    if speed_range is None:
        return 100

    minimum = speed_range.min if speed_range.min is not None else 1
    maximum = speed_range.max if speed_range.max is not None else 100
    step = speed_range.step if speed_range.step is not None and speed_range.step > 0 else 1
    if maximum < minimum:
        return 100
    return max(1, int(((maximum - minimum) / step) + 1))


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


def _product_prop(
    product_component: ComponentModel | None,
    prop_id: str,
):
    """从产品组件中查找指定属性定义。"""
    if product_component is None:
        return None
    return next((prop for prop in product_component.properties if prop.prop_id == prop_id), None)


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """从载荷中提取参数字典。"""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _range_from_mapping(payload: Mapping[str, Any]) -> NumericRange | None:
    """从映射中解析数值范围。"""
    minimum = to_int(payload.get("min"))
    maximum = to_int(payload.get("max"))
    step = to_int(payload.get("step"))
    if minimum is None and maximum is None and step is None:
        return None
    return NumericRange(min=minimum, max=maximum, step=step)


def _enum_codes(value: Any) -> list[str]:
    """递归提取枚举值编码列表。"""
    items: list[str] = []
    if isinstance(value, Mapping):
        for key in ("values", "value_list", "valueList", "enum"):
            items.extend(_enum_codes(value.get(key)))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                code = to_str(item.get("code", item.get("value", item.get("id"))))
                if code:
                    items.append(code)
            else:
                text = to_str(item)
                if text:
                    items.append(text)
    return items


def _direction_values_from_constraint(value: Any) -> dict[str, Any]:
    """从约束中提取方向值映射。"""
    mapping: dict[str, Any] = {}
    for item in _enum_items(value):
        raw_value = item.get("code", item.get("value", item.get("id")))
        direction = _to_ha_direction(raw_value, {})
        if direction is None:
            direction = _to_ha_direction(item.get("desc", item.get("name")), {})
        if direction is None or raw_value is None:
            continue
        mapping[direction] = raw_value
    return mapping


def _direction_values_from_value_list(value_list: list[Any]) -> dict[str, Any]:
    """从值列表中提取方向值映射。"""
    mapping: dict[str, Any] = {}
    for item in value_list:
        raw_value = getattr(item, "code", None)
        direction = _to_ha_direction(raw_value, {})
        if direction is None:
            direction = _to_ha_direction(getattr(item, "desc", None), {})
        if direction is None or raw_value is None:
            continue
        mapping[direction] = raw_value
    return mapping


def _enum_items(value: Any) -> list[Mapping[str, Any]]:
    """递归提取枚举项列表。"""
    items: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        for key in ("values", "value_list", "valueList", "enum"):
            items.extend(_enum_items(value.get(key)))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                items.append(item)
    return items


def _to_ha_direction(value: Any, direction_values: Mapping[str, Any]) -> str | None:
    """将原始方向值转换为 HA 方向常量。"""
    if value is None:
        return None

    for direction, raw_value in direction_values.items():
        if value == raw_value:
            return direction

    text = to_str(value)
    if not text:
        return None

    normalized = text.lower().replace("-", "_").replace(" ", "_")
    if normalized in {"forward", "fwd", "clockwise", "cw", "zheng", "zhengzhuan", "正转"}:
        return DIRECTION_FORWARD
    if normalized in {"reverse", "rev", "counterclockwise", "ccw", "fan_reverse", "fanzhuan", "反转"}:
        return DIRECTION_REVERSE
    return None


def _project_fan_name(component: ComponentInstanceModel) -> str | None:
    """从组件 ID 推断风扇显示名称。"""
    index = _component_index(component.component_id)
    if index is not None:
        return str(index)

    lowered = component.component_id.lower()
    if lowered in {"fan", "main_fan", "fan_main"}:
        return None
    if lowered.startswith("fan_"):
        text = lowered.removeprefix("fan_").replace("_", " ").strip()
        return text or None
    return _humanize_component_id(component.component_id)


def _raw_prop(prop_key: str | None) -> str | None:
    """提取去除索引前缀的原始属性键。"""
    if prop_key is None:
        return None
    return prop_key.split("-", 1)[1] if "-" in prop_key else prop_key


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
