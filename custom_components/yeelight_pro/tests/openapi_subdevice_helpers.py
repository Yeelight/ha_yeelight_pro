"""Shared fixtures for OpenAPI sub-device projection tests."""

from __future__ import annotations

from typing import Any

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates


def build_openapi_device(row: dict[str, Any]) -> dict[str, Any]:
    """Build a coordinator-ready runtime payload from one OpenAPI row."""
    builder = DevicePayloadBuilder()
    data, _gateways = builder.build_runtime_payloads(
        devices=[row],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "room-1", "name": "客厅"}],
    )
    return data[row["id"]]


def candidate_platform_components(
    device: dict[str, Any],
) -> set[tuple[str, str | None]]:
    """Return platform/component pairs projected for one runtime payload."""
    return {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    }


def openapi_prop(
    prop_id: str,
    value: Any,
    desc: str,
    fmt: str,
    *,
    unit: str | None = None,
    range_: dict[str, Any] | None = None,
    operators: list[str] | None = None,
) -> dict[str, Any]:
    """Build one OpenAPI property row."""
    payload: dict[str, Any] = {
        "propId": prop_id,
        "value": value,
        "desc": desc,
        "format": fmt,
    }
    if unit is not None:
        payload["unit"] = unit
    if range_ is not None:
        payload["valueRange"] = range_
    if operators is not None:
        payload["operators"] = operators
    return payload


__all__ = [
    "build_openapi_device",
    "candidate_platform_components",
    "openapi_prop",
]
