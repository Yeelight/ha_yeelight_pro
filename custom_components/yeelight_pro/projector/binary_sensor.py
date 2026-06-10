"""将 coordinator 运行时数据投影为 Home Assistant binary sensor 视图."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, HADeviceInstanceModel
from ..utils import to_bool, to_category, to_int, to_str, matches_category
from .device import flatten_instance_state, project_payload_device_info

# 事件型产品类型集合（仅暴露防拆状态的设备）
EVENT_STYLE_PRODUCT_TYPES = {128, 132}

# binary sensor 属性规格：key -> {component_id, label, device_class, icon, inverted}
BINARY_SENSOR_SPECS: dict[str, dict[str, str | None]] = {
    "mv": {
        "component_id": "motion",
        "label": "人体移动",
        "device_class": "motion",
        "icon": None,
        "inverted": None,
    },
    "dc": {
        "component_id": "door",
        "label": "门窗",
        "device_class": "door",
        "icon": None,
        "inverted": "true",
    },
    "alm": {
        "component_id": "tamper",
        "label": "防拆",
        "device_class": "tamper",
        "icon": None,
        "inverted": None,
    },
}

# 情景/面板类设备类别 token
_SCENE_CATEGORY_TOKENS = (
    "情景",
    "scene",
    "scene_panel",
    "panel",
    "旋钮",
    "knob",
    "knob_switch",
)


@dataclass(slots=True)
class HABinarySensorProjection:
    """投影后的 Home Assistant binary sensor 视图."""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    is_on: bool
    device_class: str | None
    device_info: dict[str, Any] | None
    icon: str | None = None


def project_binary_sensors(
    device_payload: Mapping[str, Any], *, domain: str
) -> list[HABinarySensorProjection]:
    """将 coordinator payload 投影为一个或多个 binary sensor."""
    if _is_event_style_device(device_payload):
        return []

    instance = _load_instance(device_payload)
    params = _runtime_state(device_payload, instance)
    device_info = project_payload_device_info(device_payload, instance)
    base_name = _device_name(device_payload, instance)
    device_id = str(device_payload.get("device_id", "unknown"))
    base_available = to_bool(device_payload.get("online"), default=False)
    if instance is not None:
        base_available = bool(instance.online)

    projections: list[HABinarySensorProjection] = []
    for key, spec in BINARY_SENSOR_SPECS.items():
        if key not in params:
            continue

        is_on = to_bool(params.get(key))
        if spec.get("inverted") == "true":
            is_on = not is_on

        component = _component_for_prop(instance, key)
        projections.append(
            HABinarySensorProjection(
                component_id=str(spec["component_id"]),
                unique_id=f"{domain}_{device_id}_{spec['component_id']}",
                name=_projection_name(base_name, spec["label"]),
                available=_projection_available(base_available, component),
                is_on=is_on,
                device_class=to_str(spec["device_class"]),
                device_info=device_info,
                icon=to_str(spec["icon"]),
            )
        )

    return projections


def _load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从 payload 中加载设备实例模型."""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _device_name(
    device_payload: Mapping[str, Any], instance: HADeviceInstanceModel | None
) -> str | None:
    """获取设备名称，优先使用实例名称."""
    if instance is not None and instance.name:
        return instance.name
    return to_str(device_payload.get("name"))


def _projection_name(base_name: str | None, label: str | None) -> str | None:
    """返回投影名称，当前直接使用标签."""
    return label


def _is_event_style_device(device_payload: Mapping[str, Any]) -> bool:
    """判断是否为事件型设备（情景面板/旋钮等）."""
    product_type = to_int(device_payload.get("product_type"))
    if product_type in EVENT_STYLE_PRODUCT_TYPES:
        return True

    product_model = device_payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        product = product_model.get("product")
        if isinstance(product, Mapping):
            category = to_category(product.get("category"))
            if category and matches_category(category, _SCENE_CATEGORY_TOKENS):
                return True

    category = to_category(device_payload.get("category"))
    return bool(category) and matches_category(category, _SCENE_CATEGORY_TOKENS)


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """提取 payload 中的 params 字段."""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _runtime_state(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None,
) -> dict[str, Any]:
    """合并 payload params 与实例组件状态."""
    merged = _params(device_payload)
    merged.update(flatten_instance_state(instance))
    return merged


def _component_for_prop(
    instance: HADeviceInstanceModel | None,
    prop_key: str,
) -> ComponentInstanceModel | None:
    """查找包含指定属性 key 的组件实例."""
    if instance is None:
        return None
    for component in instance.components:
        if prop_key in component.state:
            return component
    return None


def _projection_available(
    base_available: bool,
    component: ComponentInstanceModel | None,
) -> bool:
    """计算投影可用性：基础可用性与组件可用性的交集."""
    if component is None:
        return base_available
    return bool(base_available and component.available)
