"""Debug runtime helpers for Yeelight Pro services."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN

ATTR_ENTRY_ID = "entry_id"


def debug_coordinator(hass: HomeAssistant, *, entry_id: str | None = None) -> Any | None:
    """返回启用调试模式的 coordinator，可按 entry_id 限定."""
    data = debug_runtime_entry(hass, entry_id=entry_id)
    return data.get("coordinator") if isinstance(data, Mapping) else None


def debug_runtime_entry(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
) -> Mapping[str, Any] | None:
    """返回启用 debug 的 runtime entry，可按 entry_id 限定."""
    domain_data = hass.data.get(DOMAIN, {})
    if entry_id is not None:
        data = domain_data.get(entry_id)
        return _runtime_entry_if_debug(data)

    for data in domain_data.values():
        runtime = _runtime_entry_if_debug(data)
        if runtime is not None:
            return runtime
    return None


def _runtime_entry_if_debug(data: Any) -> Mapping[str, Any] | None:
    """返回启用 debug 的 runtime coordinator."""
    if isinstance(data, Mapping):
        coordinator = data.get("coordinator")
        if coordinator is not None and bool(coordinator.debug_mode):
            return data
    return None
