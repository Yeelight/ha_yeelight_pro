"""将设备信息从 canonical 模型投影为 Home Assistant 结构."""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import DeviceInfoModel, HADeviceInstanceModel


def project_device_info(instance: HADeviceInstanceModel) -> dict[str, Any] | None:
    """将 canonical 设备信息投影为 Home Assistant `DeviceInfo` 格式."""
    return project_device_info_model(instance.device_info)


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
        "default_manufacturer",
        "default_model",
        "default_name",
        "translation_key",
    ):
        value = getattr(device_info, key)
        if value is not None:
            projected[key] = value

    if device_info.translation_placeholders:
        projected["translation_placeholders"] = dict(device_info.translation_placeholders)

    return projected or None


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
