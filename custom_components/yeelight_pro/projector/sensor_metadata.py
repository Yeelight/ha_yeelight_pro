"""Registry-backed sensor projection metadata."""

from __future__ import annotations

from dataclasses import dataclass

from ..canonical.models import ComponentInstanceModel
from ..capabilities.registry import iot_registry, property_capability, property_spec
from ..entity_category import (
    ENTITY_CATEGORY_CONFIG,
    ENTITY_CATEGORY_DIAGNOSTIC,
    entity_category_for_property,
)
from ..utils import to_category
from .registry_sensor_safety import (
    registry_sensor_component_id,
    registry_sensor_icon,
    registry_sensor_label,
    safe_registry_sensor_property,
)

SENSOR_LABELS = {
    "t": ("temperature", "温度"),
    "temp": ("temperature", "温度"),
    "h": ("humidity", "湿度"),
    "luminance": ("illuminance", "光照"),
    "level": ("light_level", "光感等级"),
    "ebl": ("environment_brightness_level", "环境亮度等级"),
    "curp": ("current_power", "当前功率"),
    "iec": ("energy_consumption", "阶段电量"),
    "ap": ("active_power", "有功功率"),
    "ae": ("active_energy", "总有功"),
    "bl": ("battery", "电量"),
    "acct": ("current_temperature", "当前温度"),
    "rfhct": ("floor_heating_temperature", "地暖温度"),
    "acd": ("ac_delay_remaining", "空调延时剩余"),
    "cra": ("current_rotary_angle", "当前旋转角度"),
    "fv": ("firmware_version", "固件版本"),
    "ch_num": ("channel_count", "组件数"),
    "o": ("online_status", "在线状态"),
    "pl": ("physical_link", "物理连接"),
    "lf": ("uptime", "运行时间"),
    "fm": ("free_memory", "剩余内存"),
    "cpt": ("connectivity_protocol", "接入协议"),
    "ot": ("operating_time", "运行时长"),
    "sys_s": ("system_starts", "系统启动次数"),
    "esv": ("external_supply_voltage", "外部供电电压"),
    "esvf": ("external_supply_frequency", "外部供电频率"),
    "ocp": ("output_current_percent", "输出电流百分比"),
    "lsot": ("light_source_on_time", "光源点亮时长"),
    "lsv": ("light_source_voltage", "光源电压"),
    "lsc": ("light_source_current", "光源电流"),
    "pf": ("power_factor", "功率因数"),
}
REGISTRY_SENSOR_PROPS = frozenset(
    prop
    for prop, spec in (
        (candidate, property_spec(candidate))
        for candidate in {item.prop for item in iot_registry().properties}
    )
    if prop in SENSOR_LABELS or safe_registry_sensor_property(prop, spec)
)
DALI_ENERGY_COMPONENT = "dali energy"
DALI_ENERGY_PROJECTED_PROPS = frozenset({
    "ae",
    "ap",
    "esv",
    "esvf",
    "lsc",
    "lsot",
    "lsv",
    "ocp",
    "ot",
    "pf",
    "sys_s",
    "temp",
})
DECIVOLT_SENSOR_PROPS = frozenset({"esv", "lsv"})


@dataclass(frozen=True, slots=True)
class SensorSpec:
    """内部 sensor 投影规格."""

    component_id: str
    label: str
    device_class: str | None
    unit: str | None
    state_class: str | None = None
    icon: str | None = None


def should_project_registry_sensor(
    key: str,
    component: ComponentInstanceModel | None,
) -> bool:
    """根据组件上下文过滤已知但暂不安全暴露的遥测属性。"""
    if entity_category_for_property(key) == ENTITY_CATEGORY_CONFIG:
        return False
    if (
        component is not None
        and to_category(component.category) == DALI_ENERGY_COMPONENT
        and key not in DALI_ENERGY_PROJECTED_PROPS
    ):
        return False
    return True


def sensor_entity_category(
    prop: str,
    component: ComponentInstanceModel | None,
) -> str | None:
    """返回 sensor 的 HA 分类。"""
    category = entity_category_for_property(prop)
    if category is not None:
        return category
    if component is not None and to_category(component.category) == DALI_ENERGY_COMPONENT:
        return ENTITY_CATEGORY_DIAGNOSTIC
    return None


def registry_sensor_spec(prop: str) -> SensorSpec | None:
    """从 Yeelight IoT registry 派生 sensor 投影规格."""
    capability = property_capability(prop)
    spec = property_spec(prop)
    if spec is None or not safe_registry_sensor_property(prop, spec):
        return None
    component_id, label = SENSOR_LABELS.get(
        prop,
        (
            registry_sensor_component_id(prop, spec),
            registry_sensor_label(prop, spec),
        ),
    )
    if prop == "temp":
        component_id = "internal_temperature"
        label = "内部温度"
    unit = (capability.unit if capability is not None else None) or spec.unit
    device_class = capability.device_class if capability is not None else None
    if prop in DECIVOLT_SENSOR_PROPS:
        unit = "V"
        device_class = "voltage"
    return SensorSpec(
        component_id=component_id,
        label=label,
        device_class=device_class,
        unit=unit,
        state_class=state_class_for_device_class(device_class),
        icon=icon_for_property(prop)
        or (
            registry_sensor_icon(prop, spec)
            if capability is None or device_class is None
            else None
        ),
    )


def sensor_native_value(prop: str, value: object) -> object:
    """Return the HA-facing native value for documented sensor units."""
    if prop not in DECIVOLT_SENSOR_PROPS or isinstance(value, bool):
        return value
    if not isinstance(value, (int, float, str)):
        return value
    try:
        return float(value) / 10
    except ValueError:
        return value


def state_class_for_device_class(device_class: str | None) -> str | None:
    """返回 sensor 长期统计语义."""
    if device_class == "power":
        return "measurement"
    if device_class == "energy":
        return "total_increasing"
    if device_class in {"temperature", "humidity", "illuminance", "battery", "voltage"}:
        return "measurement"
    return None


def icon_for_property(prop: str) -> str | None:
    """返回无标准 device_class 属性的图标。"""
    return {
        "acd": "mdi:timer-sand",
        "bc": "mdi:battery-check",
        "bcg": "mdi:battery-charging",
        "ch_num": "mdi:counter",
        "cpt": "mdi:access-point-network",
        "cra": "mdi:angle-acute",
        "ebl": "mdi:brightness-6",
        "fm": "mdi:memory",
        "fv": "mdi:chip",
        "lf": "mdi:timer-outline",
        "level": "mdi:brightness-6",
        "o": "mdi:connection",
        "ot": "mdi:timer-outline",
        "pl": "mdi:ethernet",
        "sys_s": "mdi:restart",
    }.get(prop)


def _is_gateway_component(component: ComponentInstanceModel | None) -> bool:
    """判断属性是否属于网关组件。"""
    if component is None:
        return False
    return to_category(component.category) == "gateway"


__all__ = [
    "DALI_ENERGY_COMPONENT",
    "DALI_ENERGY_PROJECTED_PROPS",
    "REGISTRY_SENSOR_PROPS",
    "SENSOR_LABELS",
    "SensorSpec",
    "icon_for_property",
    "registry_sensor_spec",
    "sensor_native_value",
    "sensor_entity_category",
    "should_project_registry_sensor",
    "state_class_for_device_class",
]
