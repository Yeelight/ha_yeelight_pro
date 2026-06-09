"""Command execution wrappers for Yeelight Pro coordinator actions."""

from __future__ import annotations

from typing import Any

from .client import YeelightProClient
from .exceptions import CommandError, YeelightProError, safe_error_summary


async def async_control_device(
    client: YeelightProClient,
    *,
    house_id: int,
    device_id: int,
    params: dict[str, Any],
    duration: int,
) -> None:
    """Execute a device property command with coordinator-level error semantics."""
    try:
        await client.control_device(house_id, device_id, params, duration)
    except YeelightProError:
        raise
    except Exception as err:
        raise CommandError(
            f"Failed to control device: {safe_error_summary(err)}"
        ) from None


async def async_toggle_device(
    client: YeelightProClient,
    *,
    house_id: int,
    device_id: int,
    properties: list[str],
) -> None:
    """Execute a device toggle command with coordinator-level error semantics."""
    try:
        await client.toggle_device(house_id, device_id, properties)
    except YeelightProError:
        raise
    except Exception as err:
        raise CommandError(
            f"Failed to toggle device: {safe_error_summary(err)}"
        ) from None


async def async_execute_scene(
    client: YeelightProClient,
    *,
    house_id: int,
    scene_id: str,
) -> None:
    """Execute a scene with coordinator-level error semantics."""
    try:
        await client.execute_scene(house_id, scene_id)
    except YeelightProError:
        raise
    except Exception as err:
        raise CommandError(
            f"Failed to execute scene: {safe_error_summary(err)}"
        ) from None


async def async_trigger_automation(
    client: YeelightProClient,
    *,
    automation_id: str,
) -> None:
    """Trigger an automation with coordinator-level error semantics."""
    try:
        await client.trigger_automation(automation_id)
    except YeelightProError:
        raise
    except Exception as err:
        raise CommandError(
            f"Failed to trigger automation: {safe_error_summary(err)}"
        ) from None


async def async_control_group(
    client: YeelightProClient,
    *,
    house_id: int,
    group_id: str,
    params: dict[str, Any],
    duration: int,
) -> None:
    """Execute a group property command with coordinator-level error semantics."""
    try:
        await client.control_group(house_id, group_id, params, duration)
    except YeelightProError:
        raise
    except Exception as err:
        raise CommandError(
            f"Failed to control group: {safe_error_summary(err)}"
        ) from None
