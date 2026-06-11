"""将设备信息从 canonical 或运行时载荷投影为 Home Assistant 结构."""

from __future__ import annotations

from typing import Any, Mapping

from ..core.device_classification import is_generic_model_label
from ..canonical.models import DeviceInfoModel, HADeviceInstanceModel
from ..device_display import device_model_name


def project_device_info(instance: HADeviceInstanceModel) -> dict[str, Any] | None:
    """将 canonical 设备信息投影为 Home Assistant `DeviceInfo` 格式."""
    return project_device_info_model(instance.device_info)


def project_payload_device_info(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel | None = None,
) -> dict[str, Any] | None:
    """从 canonical 实例或顶层 fallback 载荷投影 HA device_info."""
    if instance is not None:
        projected = project_device_info(instance)
        if projected is not None:
            return projected

    payload = device_payload.get("device_info")
    if not isinstance(payload, Mapping):
        return None
    return _project_mapping_device_info(payload)


def project_device_info_model(device_info: DeviceInfoModel | None) -> dict[str, Any] | None:
    """将 canonical 设备信息模型投影为 Home Assistant 结构."""
    if device_info is None:
        return None

    projected: dict[str, Any] = {}

    if device_info.identifiers:
        projected["identifiers"] = {
            (str(domain), str(identifier))
            for domain, identifier in device_info.identifiers
        }

    if device_info.connections:
        projected["connections"] = {
            (str(connection_type), str(connection_value))
            for connection_type, connection_value in device_info.connections
        }

    if device_info.via_device and len(device_info.via_device) == 2:
        projected["via_device"] = (
            str(device_info.via_device[0]),
            str(device_info.via_device[1]),
        )

    for key in (
        "manufacturer",
        "model",
        "model_id",
        "name",
        "serial_number",
        "sw_version",
        "hw_version",
        "configuration_url",
        "entry_type",
        "suggested_area",
    ):
        value = getattr(device_info, key)
        if value is not None:
            projected[key] = value

    source = projected | {
        "name": device_info.name,
        "model": device_info.model,
        "model_id": device_info.model_id,
    }
    _normalize_projected_model(projected, source)

    return projected or None


def _project_mapping_device_info(device_info: Mapping[str, Any]) -> dict[str, Any] | None:
    """将 JSON 风格 device_info fallback 规范化为 HA DeviceInfo 结构."""
    projected: dict[str, Any] = {}

    if identifiers := _project_pair_set(device_info.get("identifiers")):
        projected["identifiers"] = identifiers
    if connections := _project_pair_set(device_info.get("connections")):
        projected["connections"] = connections
    if via_device := _project_pair(device_info.get("via_device")):
        projected["via_device"] = via_device

    for key in (
        "manufacturer",
        "model",
        "model_id",
        "name",
        "serial_number",
        "sw_version",
        "hw_version",
        "configuration_url",
        "entry_type",
        "suggested_area",
    ):
        value = device_info.get(key)
        if value is not None:
            projected[key] = value

    _normalize_projected_model(projected, device_info)

    return projected or None


def _project_pair_set(value: Any) -> set[tuple[str, str]]:
    """将 JSON pair list 转为 HA registry tuple set."""
    pairs: set[tuple[str, str]] = set()
    for item in value or []:
        pair = _project_pair(item)
        if pair is not None:
            pairs.add(pair)
    return pairs


def _project_pair(value: Any) -> tuple[str, str] | None:
    """将 JSON pair 转为 HA registry tuple."""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (str(value[0]), str(value[1]))
    return None


def _normalize_projected_model(
    projected: dict[str, Any],
    source: Mapping[str, Any],
) -> None:
    """Replace broad fallback model labels before they reach device registry."""
    model = projected.get("model")
    if model is None or not is_generic_model_label(model):
        return

    normalized = device_model_name(source)
    if normalized and not is_generic_model_label(normalized):
        projected["model"] = normalized
        return
    projected.pop("model", None)


def flatten_instance_state(instance: HADeviceInstanceModel | None) -> dict[str, Any]:
    """将组件状态展平为简单的运行时状态视图."""
    if instance is None:
        return {}

    merged: dict[str, Any] = {}
    for component in instance.components:
        state = component.state
        if not isinstance(state, Mapping):
            continue
        for key, value in state.items():
            key_text = str(key).strip()
            if not key_text or key_text in merged:
                continue
            merged[key_text] = value
    return merged
