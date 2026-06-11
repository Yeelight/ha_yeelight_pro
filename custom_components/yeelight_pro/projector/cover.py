"""将协调器运行时数据投影为 Home Assistant cover 视图."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel
from homeassistant.components.cover import CoverDeviceClass

from ..canonical.models import HADeviceInstanceModel
from ..utils import to_category
from .common import (
    load_product_model,
    payload_available,
    product_component,
    schema_backed_component_available,
)
from .device import flatten_instance_state, project_payload_device_info


@dataclass(slots=True)
class HACoverProjection:
    """投影后的 Home Assistant cover 视图."""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    current_cover_position: int | None
    target_cover_position: int | None
    is_closed: bool | None
    is_opening: bool
    is_closing: bool
    device_class: CoverDeviceClass | None
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_cover(device_payload: Mapping[str, Any], *, domain: str) -> HACoverProjection | None:
    """将协调器载荷投影为 Home Assistant cover 实体."""
    instance = _load_instance(device_payload)
    component = _select_cover_component(instance)
    if component is None and not _payload_is_cover(device_payload):
        return None

    device_id = str(device_payload.get("device_id", "unknown"))
    params = _runtime_state(device_payload, instance, component)
    current_position = _clamp_position(_int(params.get("cp")))
    target_position = _clamp_position(_int(params.get("tp")))
    available = payload_available(device_payload, instance)
    if instance is not None and component is not None:
        product_model = load_product_model(device_payload)
        available = schema_backed_component_available(
            payload_available(device_payload, instance),
            component,
            schema_component=product_component(product_model, component.component_id),
        )

    return HACoverProjection(
        component_id="cover",
        unique_id=f"{domain}_{device_id}_cover",
        name="窗帘",
        available=available,
        current_cover_position=current_position,
        target_cover_position=target_position,
        is_closed=(current_position == 0) if current_position is not None else None,
        is_opening=_is_opening(current_position, target_position),
        is_closing=_is_closing(current_position, target_position),
        device_class=CoverDeviceClass.CURTAIN,
        device_info=project_payload_device_info(device_payload, instance),
        icon=None,
    )


def _is_opening(current_position: int | None, target_position: int | None) -> bool:
    """判断窗帘是否正在打开."""
    if current_position is None or target_position is None:
        return False
    return target_position > current_position


def _is_closing(current_position: int | None, target_position: int | None) -> bool:
    """判断窗帘是否正在关闭."""
    if current_position is None or target_position is None:
        return False
    return target_position < current_position


def _clamp_position(value: int | None) -> int | None:
    """将位置值钳制到 0-100 范围."""
    if value is None:
        return None
    return max(0, min(100, value))


def _load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从载荷中加载设备实例模型."""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """提取原始参数字典."""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _select_cover_component(
    instance: HADeviceInstanceModel | None,
) -> ComponentInstanceModel | None:
    """从设备实例中选择 cover 组件."""
    if instance is None:
        return None

    for component in instance.components:
        category = _string(component.category).lower()
        if (
            category in {"cover", "curtain", "blind"}
            or component.component_id.lower() in {"cover", "curtain", "blind"}
            or any(key in component.state for key in ("cp", "tp"))
        ):
            return component
    return None


def _payload_is_cover(device_payload: Mapping[str, Any]) -> bool:
    """Return true only for documented cover/curtain runtime categories."""
    category = to_category(
        device_payload.get("iot_category")
        or device_payload.get("category")
        or device_payload.get("type")
    )
    return category in {"cover", "curtain", "blind"}


def _runtime_state(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
    component: ComponentInstanceModel | None,
) -> dict[str, Any]:
    """合并运行时状态：参数载荷 + 组件/实例状态."""
    params = _params(device_payload)
    if component is not None:
        merged = dict(params)
        merged.update(component.state)
        return merged

    state = flatten_instance_state(instance)
    if not state:
        return params

    # Canonical 实例状态优先，但原始参数可能仍包含 cover 运行时字段（如 cp/tp），
    # 这些字段尚未展平到实例组件状态中。
    merged = dict(params)
    merged.update(state)
    return merged


def _bool(value: Any, default: bool = False) -> bool:
    """安全布尔值转换."""
    if value is None:
        return default
    return bool(value)


def _int(value: Any) -> int | None:
    """安全整数转换."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string(value: Any) -> str:
    """安全字符串转换."""
    if value is None:
        return ""
    return str(value).strip()
