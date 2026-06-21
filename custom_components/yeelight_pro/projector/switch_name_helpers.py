"""Switch projection channel naming helpers."""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel
from ..device_display import channel_name_label
from ..utils import to_int
from .common import component_index
from .switch_helper_constants import RAW_SWITCH_KEY_RE

def _build_switch_name(
    base_name: str | None,
    component_id: str,
    control_key: str,
    component: ComponentInstanceModel | None = None,
    *,
    device_payload: Mapping[str, Any] | None = None,
) -> str | None:
    """构建 switch 显示名称，避免裸数字通道名."""
    index = component_index(component_id)
    if index is None:
        match = RAW_SWITCH_KEY_RE.match(control_key)
        if match:
            index = to_int(match.group("index"))
    label_component = _label_component_from_subdevice(
        device_payload,
        index=index,
    ) or component
    if label_component is None or _raw_params_are_indexed_switch_power(
        control_key,
        device_payload=device_payload,
    ):
        label_component = _synthetic_component_for_raw_key(
            control_key,
            device_payload=device_payload,
        ) or label_component
    return channel_name_label(
        index=index,
        component=label_component,
        device_payload=device_payload,
    )


def _synthetic_component_for_raw_key(
    raw_key: str,
    *,
    device_payload: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """Return label-only component evidence for raw indexed switch keys."""
    match = RAW_SWITCH_KEY_RE.match(raw_key)
    if match is None or match.group("prop") != "sp":
        return None
    if _has_indexed_power_key(device_payload):
        return None
    return {
        "component_id": f"wireless_switch_channel_{match.group('index')}",
        "io_type": "input",
    }


def _label_component_from_subdevice(
    device_payload: Mapping[str, Any] | None,
    *,
    index: int | None,
) -> Mapping[str, Any] | None:
    """Return OpenAPI sub-device metadata for channel naming."""
    if device_payload is None or index is None:
        return None
    subdevices = device_payload.get("subDeviceList")
    if not isinstance(subdevices, list):
        return None
    for item in subdevices:
        if not isinstance(item, Mapping):
            continue
        if to_int(item.get("index")) == index:
            return item
    return None


def _has_indexed_power_key(device_payload: Mapping[str, Any] | None) -> bool:
    """Return true when raw params contain indexed N-p output switch keys."""
    if device_payload is None:
        return False
    for raw_key in _params(device_payload):
        match = RAW_SWITCH_KEY_RE.match(str(raw_key))
        if match is not None and match.group("prop") == "p":
            return True
    return False


def _raw_params_are_indexed_switch_power(
    raw_key: str,
    *,
    device_payload: Mapping[str, Any] | None,
) -> bool:
    """Return true when raw params prove this component is controlled by N-sp."""
    match = RAW_SWITCH_KEY_RE.match(raw_key)
    return (
        match is not None
        and match.group("prop") == "sp"
        and not _has_indexed_power_key(device_payload)
    )


def _params(device_payload: Mapping[str, Any]) -> dict[str, Any]:
    """从 payload 中提取 params 字典."""
    params = device_payload.get("params")
    return dict(params) if isinstance(params, Mapping) else {}


def _raw_switch_sort_key(raw_key: str) -> tuple[int, str]:
    """索引开关键的排序键：按数字索引升序."""
    match = RAW_SWITCH_KEY_RE.match(raw_key)
    if not match:
        return (9999, raw_key)
    return (to_int(match.group("index")) or 9999, raw_key)
