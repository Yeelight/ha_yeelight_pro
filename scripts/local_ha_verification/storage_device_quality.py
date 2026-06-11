"""Device-registry quality checks for local HA verification."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .report import VerificationReport
from .storage_entries import has_generated_house_placeholder

GENERIC_SOURCE_MODELS = frozenset({
    "binary_sensor",
    "climate",
    "contact_sensor",
    "cover",
    "curtain",
    "event",
    "fan",
    "gateway",
    "human_sensor",
    "light",
    "light_sensor",
    "lock",
    "other",
    "relay_switch",
    "scene_panel",
    "sensor",
    "switch",
    "temp_control",
    "二元传感器",
    "事件",
    "传感器",
    "开关",
    "控制",
    "易来设备",
    "智能设备",
    "温控",
    "温控设备",
    "灯",
    "灯具",
    "继电器开关",
    "设备",
    "风扇",
})


def verify_device_registry_quality(
    devices: list[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify source devices expose friendly metadata in HA's registry."""
    source_devices = [device for device in devices if is_source_device(device)]
    if not source_devices:
        report.fail("device registry has no Yeelight Pro source devices")
        report.metric("device_registry_quality", _quality_metrics(0))
        return

    missing_name = sum(1 for device in source_devices if not _device_name(device))
    missing_model = sum(1 for device in source_devices if not device.get("model"))
    generic_model = sum(1 for device in source_devices if _is_generic_model(device))
    runtime_model_id = sum(1 for device in source_devices if _has_runtime_model_id(device))
    missing_area = sum(
        1
        for device in source_devices
        if not device.get("area_id") and not device.get("suggested_area")
    )
    house_placeholders = sum(1 for device in devices if _is_house_placeholder(device))
    _report_quality_failures(
        report,
        source_count=len(source_devices),
        missing_name=missing_name,
        missing_model=missing_model,
        generic_model=generic_model,
        runtime_model_id=runtime_model_id,
        missing_area=missing_area,
        house_placeholders=house_placeholders,
    )
    report.metric(
        "device_registry_quality",
        _quality_metrics(
            len(source_devices),
            missing_name=missing_name,
            missing_model=missing_model,
            generic_model=generic_model,
            runtime_model_id=runtime_model_id,
            missing_area=missing_area,
            house_placeholder_names=house_placeholders,
        ),
    )


def is_source_device(device: Mapping[str, Any], *, domain: str = "yeelight_pro") -> bool:
    """Return true for source devices, excluding house/gateway aggregate entries."""
    identifiers = device.get("identifiers")
    if not isinstance(identifiers, list):
        return False
    for identifier in identifiers:
        if not (
            isinstance(identifier, (list, tuple))
            and len(identifier) == 2
            and identifier[0] == domain
        ):
            continue
        if str(identifier[1]).startswith("device:"):
            return True
    return False


def _report_quality_failures(
    report: VerificationReport,
    *,
    source_count: int,
    missing_name: int,
    missing_model: int,
    generic_model: int,
    runtime_model_id: int,
    missing_area: int,
    house_placeholders: int,
) -> None:
    if missing_name:
        report.fail(
            "device registry source devices missing friendly names: "
            f"{missing_name}/{source_count}"
        )
    if missing_model:
        report.fail(
            "device registry source devices missing model metadata: "
            f"{missing_model}/{source_count}"
        )
    if generic_model:
        report.fail(
            "device registry source devices still use generic model labels: "
            f"{generic_model}/{source_count}"
        )
    if runtime_model_id:
        report.warn(
            "device registry source devices retain historical runtime model_id values: "
            f"{runtime_model_id}/{source_count}"
        )
    if missing_area:
        report.fail(
            "device registry source devices missing area metadata: "
            f"{missing_area}/{source_count}"
        )
    if house_placeholders:
        report.fail(
            "device registry still contains generated house helper names: "
            f"{house_placeholders}"
        )
    if not any((
        missing_name,
        missing_model,
        generic_model,
        missing_area,
        house_placeholders,
    )):
        report.fact(
            "device registry source metadata: "
            f"{source_count} named/modelled/area-linked devices"
        )


def _quality_metrics(
    source_devices: int,
    *,
    missing_name: int = 0,
    missing_model: int = 0,
    generic_model: int = 0,
    runtime_model_id: int = 0,
    missing_area: int = 0,
    house_placeholder_names: int = 0,
) -> dict[str, int]:
    return {
        "source_devices": source_devices,
        "missing_name": missing_name,
        "missing_model": missing_model,
        "generic_model": generic_model,
        "runtime_model_id": runtime_model_id,
        "missing_area": missing_area,
        "house_placeholder_names": house_placeholder_names,
    }


def _device_name(device: Mapping[str, Any]) -> str | None:
    """Return the effective HA device display name."""
    for key in ("name_by_user", "name"):
        value = device.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_generic_model(device: Mapping[str, Any]) -> bool:
    """Return true when HA registry still shows broad platform/category labels."""
    model = device.get("model")
    if not isinstance(model, str):
        return False
    return model.strip().lower() in GENERIC_SOURCE_MODELS


def _has_runtime_model_id(device: Mapping[str, Any]) -> bool:
    """Return true when registry model_id still exposes an internal runtime id."""
    model_id = device.get("model_id")
    return isinstance(model_id, str) and model_id.startswith("runtime-")


def _is_house_placeholder(device: Mapping[str, Any]) -> bool:
    """Return true for generated house helper labels in device registry."""
    return any(
        has_generated_house_placeholder(device.get(key))
        for key in ("name_by_user", "name")
    )


__all__ = ["is_source_device", "verify_device_registry_quality"]
