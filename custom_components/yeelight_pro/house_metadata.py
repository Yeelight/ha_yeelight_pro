"""House-level metadata helpers for Yeelight Pro entities."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from .const import CONF_HOUSE_NAME, DEFAULT_HOUSE_NAME, DOMAIN

_HOUSE_PLACEHOLDER_RE = re.compile(
    r"^(?:house|home|project|yeelight(?:\s+pro)?)\s+[\w:-]+$",
    re.IGNORECASE,
)


def house_name_from_data(entry_data: Mapping[str, Any] | None) -> str:
    """Return the friendly house name stored on a config entry."""
    if isinstance(entry_data, Mapping):
        name = friendly_house_name(entry_data.get(CONF_HOUSE_NAME))
        if name:
            return name
    return DEFAULT_HOUSE_NAME


def house_device_info(coordinator: Any, *, name_suffix: str | None = None) -> dict[str, Any]:
    """Return the shared HA device_info for house-level helper entities."""
    house_id = _text(getattr(coordinator, "house_id", None)) or "house"
    base_name = house_name_from_data(getattr(coordinator, "entry_data", None))
    return {
        "identifiers": {(DOMAIN, f"house:{house_id}"), (DOMAIN, house_id)},
        "manufacturer": "Yeelight",
        "model": "Yeelight Pro 家庭",
        "name": base_name,
    }


def house_name_from_choice(choices: Mapping[Any, str], house_id: Any) -> str:
    """Resolve a selected house id back to the friendly choice label."""
    return friendly_house_name(choices.get(house_id)) or DEFAULT_HOUSE_NAME


def friendly_house_name(value: Any) -> str | None:
    """Return a user-facing house label, dropping generated id placeholders."""
    text = _text(value)
    if text is None or is_house_placeholder_name(text):
        return None
    return text


def is_house_placeholder_name(value: Any) -> bool:
    """Return whether a house label is only a generated id placeholder."""
    text = _text(value)
    if text is None:
        return False
    return bool(_HOUSE_PLACEHOLDER_RE.match(text))


def _text(value: Any) -> str | None:
    text = str(value).strip() if value not in (None, "") else ""
    return text or None


__all__ = [
    "friendly_house_name",
    "house_device_info",
    "house_name_from_choice",
    "house_name_from_data",
    "is_house_placeholder_name",
]
