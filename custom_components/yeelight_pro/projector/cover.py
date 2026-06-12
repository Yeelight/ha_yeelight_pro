"""将协调器运行时数据投影为 Home Assistant cover 视图."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, ComponentModel
from homeassistant.components.cover import CoverDeviceClass

from ..canonical.models import HADeviceInstanceModel
from ..device_display import channel_name_label
from ..utils import to_str
from .common import (
    component_index,
    humanize_component_id,
    load_product_model,
    payload_available,
    product_component,
    schema_backed_component_available,
    state_value,
)
from .device import flatten_instance_state, project_payload_device_info
from .platform_evidence import (
    component_has_cover_evidence,
    component_prop_ids,
    payload_has_cover_evidence,
)
from .property_control_common import control_key

_LOGGER = logging.getLogger(__name__)


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
    target_position_key: str = "tp"


def project_cover(device_payload: Mapping[str, Any], *, domain: str) -> HACoverProjection | None:
    """将协调器载荷投影为 Home Assistant cover 实体."""
    covers = project_covers(device_payload, domain=domain)
    return covers[0] if covers else None


def project_covers(device_payload: Mapping[str, Any], *, domain: str) -> list[HACoverProjection]:
    """将协调器载荷投影为一个或多个 Home Assistant cover 实体."""
    instance = _load_instance(device_payload)
    if instance is None:
        legacy = _project_legacy_cover(device_payload, domain=domain)
        return [legacy] if legacy is not None else []

    product_model = load_product_model(device_payload)
    components = _cover_components(instance, product_model)
    return [
        _project_instance_cover(
            device_payload,
            instance,
            component,
            product_component=product_component(product_model, component.component_id),
            total=len(components),
            domain=domain,
        )
        for component in components
    ]


def _project_legacy_cover(
    device_payload: Mapping[str, Any], *, domain: str
) -> HACoverProjection | None:
    """兼容旧版扁平 curtain payload 的 cover 投影."""
    params = _params(device_payload)
    if not _payload_is_cover(device_payload, params):
        _LOGGER.debug(
            "Skipping legacy cover projection: device_id=%s category=%s type=%s "
            "props=%s reason=%s",
            device_payload.get("device_id"),
            device_payload.get("category"),
            device_payload.get("type"),
            sorted(str(key) for key in params),
            _payload_cover_skip_reason(device_payload, params),
        )
        return None

    device_id = str(device_payload.get("device_id", "unknown"))
    return _build_cover_projection(
        component_id="cover",
        unique_id=f"{domain}_{device_id}_cover",
        name="窗帘",
        available=payload_available(device_payload),
        state=params,
        device_info=project_payload_device_info(device_payload),
        current_position_key="cp",
        target_position_key="tp",
    )


def _project_instance_cover(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
    component: ComponentInstanceModel,
    *,
    product_component: ComponentModel | None,
    total: int,
    domain: str,
) -> HACoverProjection:
    """投影单个 canonical curtain component."""
    params = _runtime_state(device_payload, instance, component)
    available = schema_backed_component_available(
        payload_available(device_payload, instance),
        component,
        schema_component=product_component,
    )
    return _build_cover_projection(
        component_id=component.component_id,
        unique_id=f"{domain}_{instance.device_id}_{component.component_id}",
        name=_project_cover_name(component, total=total, device_payload=device_payload),
        available=available,
        state=params,
        device_info=project_payload_device_info(device_payload, instance),
        current_position_key=control_key(instance, component.component_id, "cp"),
        target_position_key=control_key(instance, component.component_id, "tp"),
    )


def _build_cover_projection(
    component_id: str,
    unique_id: str,
    name: str | None,
    available: bool,
    state: Mapping[str, Any],
    device_info: dict[str, Any] | None,
    current_position_key: str,
    target_position_key: str,
) -> HACoverProjection:
    """根据运行时状态构造 Home Assistant cover projection."""
    current_position = _clamp_position(_int(state_value(state, current_position_key)))
    target_position = _clamp_position(_int(state_value(state, target_position_key)))
    return HACoverProjection(
        component_id=component_id,
        unique_id=unique_id,
        name=name,
        available=available,
        current_cover_position=current_position,
        target_cover_position=target_position,
        is_closed=(current_position == 0) if current_position is not None else None,
        is_opening=_is_opening(current_position, target_position),
        is_closing=_is_closing(current_position, target_position),
        device_class=CoverDeviceClass.CURTAIN,
        device_info=device_info,
        icon=None,
        target_position_key=target_position_key,
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


def _cover_components(
    instance: HADeviceInstanceModel | None,
    product_model: Any | None,
) -> list[ComponentInstanceModel]:
    """返回所有具备 cover 证据的组件，按原始组件顺序稳定排序."""
    if instance is None:
        return []

    components: list[ComponentInstanceModel] = []
    for component in instance.components:
        schema_component = product_component(product_model, component.component_id)
        if component_has_cover_evidence(component, schema_component):
            components.append(component)
            continue
        _LOGGER.debug(
            "Skipping cover component projection: device_id=%s component_id=%s "
            "category=%s product_category=%s props=%s reason=%s",
            instance.device_id,
            component.component_id,
            component.category,
            None if schema_component is None else schema_component.category,
            sorted(component_prop_ids(component, schema_component)),
            _cover_component_skip_reason(component, schema_component),
        )
    return components


def _payload_is_cover(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Return true only for documented cover/curtain runtime categories."""
    return payload_has_cover_evidence(device_payload, state)


def _payload_cover_skip_reason(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> str:
    """Return why a flat payload cannot be projected as cover."""
    if not {"cp", "tp", "rs"} & set(state):
        return "missing_cover_position_properties"
    if not payload_has_cover_evidence(device_payload, state):
        return "missing_cover_capability_evidence"
    return "unknown"


def _cover_component_skip_reason(
    component: ComponentInstanceModel,
    schema_component: ComponentModel | None,
) -> str:
    """Return why a component was not projected as cover."""
    props = component_prop_ids(component, schema_component)
    if not {"cp", "tp", "rs"} & props:
        return "missing_cover_position_properties"
    return "missing_cover_capability_evidence"


def _project_cover_name(
    component: ComponentInstanceModel,
    *,
    total: int,
    device_payload: Mapping[str, Any],
) -> str | None:
    """Return HA cover entity name, preserving single-cover compatibility."""
    if total <= 1 and _is_primary_cover_component(component):
        return "窗帘"

    index = component_index(component.component_id)
    if channel := channel_name_label(
        index=index,
        component=component,
        device_payload=device_payload,
    ):
        return channel

    for value in (component.name, component.desc):
        if text := to_str(value):
            return text
    return humanize_component_id(component.component_id)


def _is_primary_cover_component(component: ComponentInstanceModel) -> bool:
    """Return true for the historical single curtain component shape."""
    return component.component_id in {"cover", "curtain"}


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
def _int(value: Any) -> int | None:
    """安全整数转换."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
