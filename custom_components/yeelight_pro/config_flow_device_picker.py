"""Cloud device picker helpers for Yeelight Pro config flow."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES
from .core.client import YeelightProClient
from .device_filter import canonical_device_import_filter
from .utils import to_str

NO_DEVICE_SELECTED_SENTINEL = "__yeelight_pro_no_device_selected__"


@dataclass(frozen=True, slots=True)
class DevicePickerChoice:
    """One cloud device option shown during config flow."""

    device_id: str
    label: str


def device_choices(devices: Sequence[Mapping[str, Any]]) -> tuple[DevicePickerChoice, ...]:
    """Return stable, user-readable choices from Open API device rows."""
    choices: dict[str, DevicePickerChoice] = {}
    for device in devices:
        device_id = _device_id(device)
        if device_id is None:
            continue
        choices[device_id] = DevicePickerChoice(
            device_id=device_id,
            label=_device_label(device, device_id),
        )
    return tuple(sorted(choices.values(), key=lambda item: (item.label, item.device_id)))


def cloud_devices_schema(
    choices: Sequence[DevicePickerChoice],
    selected_device_ids: Sequence[str],
) -> vol.Schema:
    """Return the config-flow schema for real cloud device selection."""
    return vol.Schema({
        vol.Optional(
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
            default=list(selected_device_ids),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": choice.device_id, "label": choice.label}
                    for choice in choices
                ],
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        )
    })


def device_import_filter_for_selected_devices(
    selected_device_ids: Sequence[Any],
    choices: Sequence[DevicePickerChoice],
) -> dict[str, Any]:
    """Build stored import-filter options from selected picker devices."""
    all_device_ids = [choice.device_id for choice in choices]
    selected = {
        device_id
        for value in selected_device_ids
        if (device_id := to_str(value)) is not None and device_id in all_device_ids
    }
    if not all_device_ids or selected == set(all_device_ids):
        return canonical_device_import_filter({"enabled": False})

    if not selected:
        selected = {NO_DEVICE_SELECTED_SENTINEL}

    return canonical_device_import_filter({
        "enabled": True,
        "mode": "or",
        "include": {"devices": sorted(selected)},
        "exclude": {},
    })


async def async_load_device_choices(
    hass: HomeAssistant,
    *,
    domain: str,
    access_token: str,
    house_id: int,
    client_id: str | None = None,
) -> tuple[DevicePickerChoice, ...]:
    """Load and normalize the real device list for one cloud house."""
    client = YeelightProClient(
        domain=domain,
        access_token=access_token,
        client_id=client_id,
        session=async_get_clientsession(hass),
    )
    return device_choices(await client.get_devices(house_id))


def selected_device_ids_from_input(
    user_input: Mapping[str, Any] | None,
    choices: Sequence[DevicePickerChoice],
) -> list[str]:
    """Return selected ids from HA form input, defaulting to all devices."""
    if user_input is None:
        return [choice.device_id for choice in choices]
    raw_value = user_input.get(CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES, [])
    if isinstance(raw_value, str):
        values: Sequence[Any] = [raw_value]
    elif isinstance(raw_value, Sequence):
        values = raw_value
    else:
        values = []
    allowed_device_ids = {choice.device_id for choice in choices}
    return [
        device_id
        for value in values
        if (device_id := to_str(value)) is not None
        and device_id in allowed_device_ids
    ]


def _device_id(device: Mapping[str, Any]) -> str | None:
    """Return the first supported Open API device id field."""
    for key in ("device_id", "deviceId", "id"):
        value = to_str(device.get(key))
        if value is not None:
            return value
    return None


def _device_label(device: Mapping[str, Any], device_id: str) -> str:
    """Return a readable label without storing raw device payloads."""
    name = (
        to_str(device.get("name"))
        or to_str(device.get("deviceName"))
        or to_str(device.get("device_name"))
        or f"Device {device_id}"
    )
    category = to_str(device.get("category"))
    room = to_str(device.get("roomName")) or to_str(device.get("room_name"))
    details = " / ".join(item for item in (category, room) if item)
    return f"{name} ({details})" if details else name


__all__ = [
    "DevicePickerChoice",
    "async_load_device_choices",
    "cloud_devices_schema",
    "device_choices",
    "device_import_filter_for_selected_devices",
    "selected_device_ids_from_input",
]
