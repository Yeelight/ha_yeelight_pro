"""Helpers for private push control-echo probing."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

import aiohttp

from custom_components.yeelight_pro.const import (
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
)
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.deployment_urls import (
    deployment_private_push_base_url,
    deployment_push_base_url,
)
from scripts.private_push_probe.push_probe import probe_push


async def execute_probe_controls(
    client: YeelightProClient,
    *,
    house_id: int,
    device_id: int,
    property_name: str,
    index: int,
    current_value: Any,
    flip_restore: bool,
    restore_delay_seconds: float,
) -> list[dict[str, Any]]:
    """Run write probes and always restore boolean flip probes."""
    if not flip_restore:
        result = await write_property(
            client,
            house_id=house_id,
            device_id=device_id,
            property_name=property_name,
            index=index,
            value=current_value,
        )
        return [safe_control_result("same_value", result)]

    flipped_value = not current_value
    results: list[dict[str, Any]] = []
    try:
        flipped = await write_property(
            client,
            house_id=house_id,
            device_id=device_id,
            property_name=property_name,
            index=index,
            value=flipped_value,
        )
        results.append(safe_control_result("flip", flipped))
        await asyncio.sleep(restore_delay_seconds)
    finally:
        restored = await write_property(
            client,
            house_id=house_id,
            device_id=device_id,
            property_name=property_name,
            index=index,
            value=current_value,
        )
        results.append(safe_control_result("restore", restored))
    return results


async def write_property(
    client: YeelightProClient,
    *,
    house_id: int,
    device_id: int,
    property_name: str,
    index: int,
    value: Any,
) -> Mapping[str, Any]:
    """Write one indexed device property."""
    return await client.control_node_properties(
        house_id=house_id,
        node_kind="device",
        resource_id=device_id,
        command="set",
        params={property_name: value},
        index=index,
        duration=0,
    )


async def probe_push_echo(
    *,
    session: aiohttp.ClientSession,
    token: str,
    push_base_url: str,
    topology: Any,
    duration_seconds: float,
    max_frames: int,
) -> dict[str, Any]:
    """Run the existing topology-aware push probe and return its summary."""
    summary = await probe_push(
        session=session,
        token=token,
        push_base_url=push_base_url,
        topology=topology,
        duration_seconds=duration_seconds,
        max_frames=max_frames,
    )
    payload = summary.as_dict()
    return {
        key: payload.get(key)
        for key in (
            "connected",
            "subscribe_sent",
            "frames_seen",
            "control_frames",
            "data_frames",
            "prop_updates",
            "event_payloads",
            "matched_loaded_topology",
            "not_loaded",
            "maybe_filtered",
            "last_error_type",
            "last_close_code",
            "last_close_exception_type",
            "update_samples",
        )
    }


async def resolve_device(
    client: YeelightProClient,
    *,
    house_id: int,
    device_id: str,
    target_name: str,
) -> Mapping[str, Any]:
    """Resolve a device by id or exact name."""
    devices = await client.get_devices(house_id)
    if device_id:
        for device in devices:
            if str(device.get("id")) == str(device_id):
                return device
        raise SystemExit("target device id not found")
    matches = [device for device in devices if str(device.get("name") or "") == target_name]
    if len(matches) != 1:
        raise SystemExit(f"target device name matched {len(matches)} devices")
    return matches[0]


def read_property_value(payload: Mapping[str, Any], prop: str) -> Any:
    """Extract a property value from Open API read response."""
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise SystemExit("read response does not contain data list")
    for row in rows:
        if isinstance(row, Mapping) and row.get("propId") == prop:
            return row.get("value")
    raise SystemExit(f"property {prop!r} not found in read response")


def push_base_url(data: Mapping[str, Any], *, override: str = "") -> str:
    """Return private push base URL from config-entry data."""
    if override.strip():
        return deployment_push_base_url(override)
    private_domain = data.get(CONF_PRIVATE_DOMAIN)
    private_push = data.get(CONF_PRIVATE_PUSH_DOMAIN)
    return deployment_private_push_base_url(private_domain, private_push)


def safe_control_result(step: str, value: Mapping[str, Any]) -> dict[str, Any]:
    """Return diagnostics-safe control result fields."""
    return {
        "step": step,
        "success": value.get("success"),
        "code": value.get("code"),
        "msg": value.get("msg"),
    }


def load_entry(config_dir: Path, entry_title: str) -> dict[str, Any]:
    """Load a Yeelight Pro config entry by title."""
    payload = json.loads(
        (config_dir / ".storage" / "core.config_entries").read_text(encoding="utf-8")
    )
    matches = [
        entry
        for entry in payload.get("data", {}).get("entries", [])
        if isinstance(entry, dict)
        and entry.get("domain") == "yeelight_pro"
        and entry.get("title") == entry_title
    ]
    if len(matches) != 1:
        raise SystemExit(f"entry title matched {len(matches)} entries")
    return matches[0]


def token_from_file(path: Path | None, *, fallback: str) -> str:
    """Read an optional token file without ever logging the token value."""
    if path is None:
        return fallback
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit(f"token file is empty: {path}")
    return token
