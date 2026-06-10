"""Coordinator helpers for Yeelight Pro LAN gateway control."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .exceptions import CommandError, YeelightProError, safe_error_summary


async def async_try_lan_control_device(
    lan_runtime: Any,
    *,
    device_id: int,
    params: Mapping[str, Any],
    duration: int,
) -> bool:
    """Send a device property command through an active LAN runtime if possible."""
    return await _async_try_send_lan_properties(
        lan_runtime,
        nodes=[
            {
                "id": device_id,
                "nt": 2,
                "duration": duration,
                "set": dict(params),
            }
        ],
        action="control device",
    )


async def async_try_lan_toggle_device(
    lan_runtime: Any,
    *,
    device_id: int,
    properties: list[str],
) -> bool:
    """Send a device toggle command through an active LAN runtime if possible."""
    if not properties:
        return False
    return await _async_try_send_lan_properties(
        lan_runtime,
        nodes=[{"id": device_id, "nt": 2, "toggle": list(properties)}],
        action="toggle device",
    )


async def async_try_lan_control_group(
    lan_runtime: Any,
    *,
    group_id: str,
    params: Mapping[str, Any],
    duration: int,
) -> bool:
    """Send a group property command through an active LAN runtime if possible."""
    node_id = _lan_uint_id(group_id)
    if node_id is None:
        return False
    return await _async_try_send_lan_properties(
        lan_runtime,
        nodes=[
            {
                "id": node_id,
                "nt": 4,
                "duration": duration,
                "set": dict(params),
            }
        ],
        action="control group",
    )


async def async_try_lan_execute_scene(
    lan_runtime: Any,
    *,
    scene_id: str,
    duration: int = 500,
) -> bool:
    """Send a scene execution command through an active LAN runtime if possible."""
    node_id = _lan_uint_id(scene_id)
    if node_id is None:
        return False
    return await _async_try_send_lan_properties(
        lan_runtime,
        nodes=[],
        scenes=[{"id": node_id, "duration": duration}],
        action="execute scene",
    )


async def _async_try_send_lan_properties(
    lan_runtime: Any,
    *,
    nodes: list[Mapping[str, Any]],
    action: str,
    scenes: list[Mapping[str, Any]] | None = None,
) -> bool:
    """Send one gateway_set.prop frame when the LAN runtime is connected."""
    if not _lan_runtime_connected(lan_runtime):
        return False
    send = getattr(lan_runtime, "async_set_properties", None)
    if not callable(send):
        return False
    try:
        await send(nodes, scenes=scenes) if scenes is not None else await send(nodes)
    except YeelightProError:
        raise
    except Exception as err:
        raise CommandError(
            f"Failed to {action} over LAN: {safe_error_summary(err)}"
        ) from None
    return True


def _lan_runtime_connected(lan_runtime: Any) -> bool:
    """Return whether the runtime reports an active TCP connection."""
    health = getattr(lan_runtime, "health", None)
    as_dict = getattr(health, "as_dict", None)
    if not callable(as_dict):
        return False
    try:
        data = as_dict()
    except Exception:
        return False
    return bool(
        isinstance(data, Mapping)
        and data.get("running") is True
        and data.get("connected") is True
    )


def _lan_uint_id(value: Any) -> int | None:
    """Return an unsigned LAN node id or None when a cloud id is not LAN-safe."""
    if isinstance(value, bool):
        return None
    try:
        node_id = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return node_id if node_id >= 0 else None


__all__ = [
    "async_try_lan_control_device",
    "async_try_lan_control_group",
    "async_try_lan_execute_scene",
    "async_try_lan_toggle_device",
]
