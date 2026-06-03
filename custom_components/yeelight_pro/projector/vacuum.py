"""将协调器运行时数据投影为 Home Assistant vacuum 视图."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.components.vacuum import VacuumEntityFeature

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..utils import to_bool, to_int, to_str, to_category, matches_category
from .device import project_device_info

# 扫地机器人相关类别标识
VACUUM_TOKENS = ("vacuum", "robot", "扫地", "吸尘", "roborock", "dreame")
NON_VACUUM_TOKENS = (
    "light", "lamp", "switch", "fan", "cover", "curtain",
    "climate", "heater", "lock", "door", "sensor",
    "灯", "开关", "风扇", "窗帘", "空调", "门锁",
)

# 设备原始状态 → HA 真空状态映射
_STATUS_MAP: dict[str, str] = {
    "cleaning": "cleaning",
    "sweeping": "cleaning",
    "mopping": "cleaning",
    "cleaning_mopping": "cleaning",
    "charging": "charging",
    "charged": "charging",
    "idle": "idle",
    "standby": "idle",
    "docked": "docked",
    "returning": "returning",
    "going_home": "returning",
    "paused": "paused",
    "error": "error",
    "fault": "error",
    "manual": "idle",
    "sleeping": "idle",
}

# 原始参数中常见的扫地机器人属性键
_VACUUM_PROP_KEYS = {
    "status": ("status", "state", "run_state", "robot_status"),
    "battery": ("battery", "battery_level", "bl"),
    "fan_speed": ("fan_speed", "suction", "vacuum_speed", "fs"),
    "charging": ("charging", "is_charging", "chg"),
}


@dataclass(slots=True)
class HAVacuumProjection:
    """投影后的 Home Assistant vacuum 视图."""

    unique_id: str
    name: str | None
    available: bool
    battery_level: int | None
    status: str
    fan_speed: int | None
    fan_speed_list: list[str]
    supported_features: VacuumEntityFeature
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_vacuum(
    device_payload: Mapping[str, Any], *, domain: str
) -> HAVacuumProjection | None:
    """将协调器载荷投影为 Home Assistant vacuum 实体.

    优先基于实例模型投影，若无匹配则回退到原始参数投影。
    """
    instance = _load_instance(device_payload)

    # 尝试基于实例模型匹配
    projection = _project_instance_vacuum(device_payload, instance, domain=domain)
    if projection is not None:
        return projection

    # 回退到原始参数投影
    return _project_raw_vacuum(device_payload, instance, domain=domain)


# ---------------------------------------------------------------------------
# 实例模型投影
# ---------------------------------------------------------------------------


def _project_instance_vacuum(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    *,
    domain: str,
) -> HAVacuumProjection | None:
    """基于 HADeviceInstanceModel 投影 vacuum 组件."""
    if instance is None:
        return None

    component = _select_vacuum_component(instance)
    if component is None:
        return None

    device_id = str(device_payload.get("device_id", instance.device_id))
    params = _params(device_payload)
    state = _merge_state(params, component)

    battery = _first_int(state, _VACUUM_PROP_KEYS["battery"])
    status_raw = _first_str(state, _VACUUM_PROP_KEYS["status"])
    fan_speed = _first_int(state, _VACUUM_PROP_KEYS["fan_speed"])
    is_charging = _first_bool(state, _VACUUM_PROP_KEYS["charging"])

    ha_status = _map_status(status_raw, is_charging)
    available = bool(instance.online and component.available)

    return HAVacuumProjection(
        unique_id=f"{domain}_{device_id}_vacuum",
        name=None,
        available=available,
        battery_level=_clamp_battery(battery),
        status=ha_status,
        fan_speed=fan_speed,
        fan_speed_list=["low", "medium", "high", "max"],
        supported_features=_default_supported_features(),
        device_info=project_device_info(instance),
        icon="mdi:robot-vacuum",
    )


# ---------------------------------------------------------------------------
# 原始参数投影（回退路径）
# ---------------------------------------------------------------------------


def _project_raw_vacuum(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    *,
    domain: str,
) -> HAVacuumProjection | None:
    """基于原始 params 投影 vacuum（无实例模型时的回退路径）."""
    device_type = to_str(device_payload.get("type"))
    category = to_category(device_payload.get("category"))

    # 非扫地机器人设备直接跳过
    if device_type and not matches_category(device_type, VACUUM_TOKENS):
        if not matches_category(category, VACUUM_TOKENS):
            return None
    elif not category and not matches_category(device_type or "", VACUUM_TOKENS):
        return None

    device_id = str(device_payload.get("device_id", "unknown"))
    params = _params(device_payload)
    available = to_bool(device_payload.get("online"), default=False)

    battery = _first_int(params, _VACUUM_PROP_KEYS["battery"])
    status_raw = _first_str(params, _VACUUM_PROP_KEYS["status"])
    fan_speed = _first_int(params, _VACUUM_PROP_KEYS["fan_speed"])
    is_charging = _first_bool(params, _VACUUM_PROP_KEYS["charging"])

    ha_status = _map_status(status_raw, is_charging)

    return HAVacuumProjection(
        unique_id=f"{domain}_{device_id}_vacuum",
        name=None,
        available=available,
        battery_level=_clamp_battery(battery),
        status=ha_status,
        fan_speed=fan_speed,
        fan_speed_list=["low", "medium", "high", "max"],
        supported_features=_default_supported_features(),
        device_info=project_device_info(instance) if instance is not None else None,
        icon="mdi:robot-vacuum",
    )


# ---------------------------------------------------------------------------
# 辅助：实例加载与组件选择
# ---------------------------------------------------------------------------


def _load_instance(
    device_payload: Mapping[str, Any],
) -> HADeviceInstanceModel | None:
    """从 payload 中加载 HADeviceInstanceModel."""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _select_vacuum_component(
    instance: HADeviceInstanceModel,
) -> ComponentInstanceModel | None:
    """从设备实例中选择 vacuum 组件."""
    for component in instance.components:
        category = to_category(component.category)
        component_id_lower = component.component_id.lower()

        # 通过 category 或 component_id 匹配
        if matches_category(category, VACUUM_TOKENS):
            return component
        if any(token in component_id_lower for token in VACUUM_TOKENS):
            return component

        # 通过特征属性判断
        state_keys = set(component.state.keys())
        has_status = bool(state_keys & {"status", "state", "run_state", "robot_status"})
        has_battery = bool(state_keys & {"battery", "battery_level", "bl"})
        if has_status and has_battery:
            if not matches_category(category, NON_VACUUM_TOKENS):
                return component
    return None


# ---------------------------------------------------------------------------
# 辅助：状态解析
# ---------------------------------------------------------------------------


def _merge_state(
    params: dict[str, Any],
    component: ComponentInstanceModel,
) -> dict[str, Any]:
    """合并原始参数与组件状态."""
    merged = dict(params)
    merged.update(component.state)
    return merged


def _map_status(raw_status: str | None, is_charging: bool | None) -> str:
    """将原始状态映射为 HA 标准真空状态.

    充电状态优先于原始状态值。
    """
    if is_charging:
        return "charging"
    if raw_status is None:
        return "idle"
    return _STATUS_MAP.get(raw_status.lower().strip(), "idle")


def _default_supported_features() -> VacuumEntityFeature:
    """返回默认支持的功能标志位."""
    return (
        VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.BATTERY
        | VacuumEntityFeature.STATUS
    )


def _clamp_battery(value: int | None) -> int | None:
    """将电量值钳制到 0-100 范围."""
    if value is None:
        return None
    return max(0, min(100, value))


# ---------------------------------------------------------------------------
# 辅助：数据提取
# ---------------------------------------------------------------------------


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """从 payload 中提取 params 字典."""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _first_int(state: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    """从状态字典中按优先级提取第一个匹配的整数值."""
    for key in keys:
        if key in state:
            return to_int(state[key])
    return None


def _first_str(state: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    """从状态字典中按优先级提取第一个匹配的字符串值."""
    for key in keys:
        if key in state:
            return to_str(state[key])
    return None


def _first_bool(state: Mapping[str, Any], keys: tuple[str, ...]) -> bool | None:
    """从状态字典中按优先级提取第一个匹配的布尔值."""
    for key in keys:
        if key in state:
            return to_bool(state[key])
    return None
