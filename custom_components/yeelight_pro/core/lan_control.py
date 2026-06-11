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
    duration: int = 500,
    delay: int | None = None,
    delayoff: int | None = None,
) -> bool:
    """Send a device property command through an active LAN runtime if possible."""
    node: dict[str, Any] = {
        "id": device_id,
        "nt": 2,
        "duration": duration,
        "set": dict(params),
    }
    if delay is not None:
        node["delay"] = delay
    if delayoff is not None:
        node["delayoff"] = delayoff
    return await _async_try_send_lan_properties(
        lan_runtime,
        nodes=[node],
        action="control device",
    )


async def async_try_lan_adjust_device(
    lan_runtime: Any,
    *,
    device_id: int,
    adjust: Mapping[str, Any],
) -> bool:
    """Send a device adjust command (relative value change) over LAN.

    adjust 格式: {"l": "-10/100", "ct": "-1/5"}
    分母 = 预设档位总数，分子 = 增减档位数（带正负号）
    """
    if not adjust:
        return False
    return await _async_try_send_lan_properties(
        lan_runtime,
        nodes=[{"id": device_id, "nt": 2, "adjust": dict(adjust)}],
        action="adjust device",
    )


async def async_try_lan_action_device(
    lan_runtime: Any,
    *,
    device_id: int,
    action: Mapping[str, Any],
) -> bool:
    """Send a device action command (blink, motorAdjust, delayCancel) over LAN.

    action 格式: {"blink": {"repeat": 4, "type": "urgent"}}
                  {"motorAdjust": {"type": "pause"}}
                  {"delayCancel": {"type": "off", "addr": 1}}
    """
    if not action:
        return False
    return await _async_try_send_lan_properties(
        lan_runtime,
        nodes=[{"id": device_id, "nt": 2, "action": dict(action)}],
        action="device action",
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
    duration: int = 500,
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


async def async_try_lan_simulate_event(
    lan_runtime: Any,
    *,
    device_id: int,
    event_type: str,
    params: Mapping[str, Any] | None = None,
) -> bool:
    """Send a virtual sensor event simulation over LAN.

    协议规范：gateway_set.event 用于模拟传感器事件触发。
    event_type 示例: "panel.click", "motion.true", "contact.open"
    params 示例: {"key": 3, "count": 1}
    """
    node: dict[str, Any] = {
        "id": device_id,
        "nt": 2,
        "value": event_type,
    }
    if params:
        node["params"] = dict(params)
    if not _lan_runtime_connected(lan_runtime):
        return False
    send = getattr(lan_runtime, "async_send_and_wait", None)
    if not callable(send):
        return False
    builder = getattr(lan_runtime, "_builder", None)
    if builder is None:
        return False
    message = builder.set_event(nodes=[node])
    try:
        ack = await send(message)
    except YeelightProError:
        raise
    except Exception as err:
        raise CommandError(
            f"Failed to simulate event over LAN: {safe_error_summary(err)}"
        ) from None
    if isinstance(ack, Mapping) and ack.get("result") == "error":
        error_data = ack.get("data", {})
        raise CommandError(f"LAN simulate event rejected: {error_data}")
    return True


async def _async_try_send_lan_properties(
    lan_runtime: Any,
    *,
    nodes: list[Mapping[str, Any]],
    action: str,
    scenes: list[Mapping[str, Any]] | None = None,
) -> bool:
    """Send one gateway_set.prop frame when the LAN runtime is connected.

    等待网关 ACK 响应，若 result 为 error 则抛出 CommandError。
    """
    if not _lan_runtime_connected(lan_runtime):
        return False
    send = getattr(lan_runtime, "async_set_properties", None)
    if not callable(send):
        return False
    try:
        ack = await send(nodes, scenes=scenes) if scenes is not None else await send(nodes)
    except YeelightProError:
        raise
    except Exception as err:
        raise CommandError(
            f"Failed to {action} over LAN: {safe_error_summary(err)}"
        ) from None
    # 检查 ACK 结果
    if isinstance(ack, Mapping) and ack.get("result") == "error":
        error_data = ack.get("data", {})
        raise CommandError(
            f"LAN {action} rejected: {error_data}"
        )
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
    "async_try_lan_action_device",
    "async_try_lan_adjust_device",
    "async_try_lan_control_device",
    "async_try_lan_control_group",
    "async_try_lan_execute_scene",
    "async_try_lan_simulate_event",
    "async_try_lan_toggle_device",
]
