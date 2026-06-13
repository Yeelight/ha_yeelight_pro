"""Scoped identity helpers for Yeelight Pro registry objects."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
import hashlib
import re
from typing import Any

from .config_flow_account import UNKNOWN_ACCOUNT_KEY, account_key_from_entry_data
from .const import (
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_REGION,
    DEFAULT_LAN_GATEWAY_PORT,
    DOMAIN,
)
from .utils import to_str

IDENTITY_SCOPE_KEY = "_yeelight_identity_scope"
_ID_PART_RE = re.compile(r"[^a-zA-Z0-9]+")


def entry_identity_scope(entry_data: Mapping[str, Any] | None, house_id: Any = None) -> str:
    """Return a stable connection/account/house isolation scope for HA registry ids."""
    data = entry_data if isinstance(entry_data, Mapping) else {}
    mode = _safe_part(data.get(CONF_CONNECTION_MODE) or CONNECTION_MODE_CLOUD)
    resolved_house_id = to_str(
        house_id if house_id not in (None, "") else data.get(CONF_HOUSE_ID)
    )
    house_part = _safe_part(resolved_house_id or "0")

    if mode == CONNECTION_MODE_CLOUD:
        region = _safe_part(data.get(CONF_CLOUD_REGION) or DEFAULT_CLOUD_REGION)
        account_key = account_key_from_entry_data(dict(data))
        account = _safe_part(UNKNOWN_ACCOUNT_KEY) if account_key == UNKNOWN_ACCOUNT_KEY else _fingerprint(account_key)
        return f"{CONNECTION_MODE_CLOUD}_{region}_account_{account}_house_{house_part}"

    if mode == CONNECTION_MODE_LAN:
        host = to_str(data.get(CONF_LAN_GATEWAY_IP)) or "gateway"
        port = to_str(data.get(CONF_LAN_GATEWAY_PORT)) or str(DEFAULT_LAN_GATEWAY_PORT)
        gateway = _fingerprint(f"{host}:{port}")
        return f"{CONNECTION_MODE_LAN}_gateway_{gateway}_house_{house_part}"

    endpoint = to_str(data.get(CONF_PRIVATE_DOMAIN)) or "endpoint"
    endpoint_key = _fingerprint(endpoint)
    mode_part = CONNECTION_MODE_PRIVATE if mode == CONNECTION_MODE_PRIVATE else mode
    return f"{mode_part}_endpoint_{endpoint_key}_house_{house_part}"


def coordinator_identity_scope(coordinator: Any) -> str:
    """Return the registry isolation scope for a loaded coordinator."""
    return entry_identity_scope(
        getattr(coordinator, "entry_data", None),
        getattr(coordinator, "house_id", None),
    )


def entity_unique_id_prefix(coordinator: Any) -> str:
    """Return the domain-prefixed HA entity unique_id prefix for a coordinator."""
    return f"{DOMAIN}_{coordinator_identity_scope(coordinator)}"


def entity_unique_id(coordinator: Any, *parts: Any) -> str:
    """Return a scoped HA entity unique_id for non-device topology entities."""
    return scoped_entity_unique_id(coordinator_identity_scope(coordinator), *parts)


def device_entity_unique_id(coordinator: Any, device_id: Any, *parts: Any) -> str:
    """Return a scoped HA entity unique_id for device-backed fallback entities."""
    return scoped_entity_unique_id(
        coordinator_identity_scope(coordinator),
        "device",
        device_id,
        *parts,
    )


def scoped_entity_unique_id(scope: str, *parts: Any) -> str:
    """Return a domain-prefixed HA entity unique_id for an explicit identity scope."""
    safe_parts = [_safe_part(part) for part in parts]
    return "_".join([DOMAIN, _safe_part(scope), *[part for part in safe_parts if part]])


def payload_entity_unique_id_prefix(
    device_payload: Mapping[str, Any],
    *,
    domain: str = DOMAIN,
) -> str:
    """Return the projector unique_id prefix, using runtime scope when present."""
    scope = to_str(device_payload.get(IDENTITY_SCOPE_KEY))
    return f"{domain}_{_safe_part(scope)}_device" if scope else domain


def apply_identity_scope_to_device_maps(
    *,
    entry_data: Mapping[str, Any] | None,
    house_id: Any,
    devices: MutableMapping[Any, dict[str, Any]],
    gateways: MutableMapping[Any, dict[str, Any]] | None = None,
) -> None:
    """Attach scoped device identifiers to normalized runtime device maps."""
    scope = entry_identity_scope(entry_data, house_id)
    for payload in devices.values():
        apply_identity_scope_to_device_payload(payload, scope=scope)
    if gateways is not None:
        for payload in gateways.values():
            apply_identity_scope_to_device_payload(payload, scope=scope)


def apply_identity_scope_to_device_payload(
    payload: MutableMapping[str, Any],
    *,
    scope: str,
) -> None:
    """Attach scoped unique-id context and HA device identifiers to one payload."""
    payload[IDENTITY_SCOPE_KEY] = scope
    device_id = _source_device_id(payload)
    if device_id is None:
        return

    scoped_identifier = [DOMAIN, scoped_device_identifier(scope, device_id)]
    via_device = _scoped_via_device(payload, scope)

    device_info = payload.get("device_info")
    if isinstance(device_info, MutableMapping):
        _apply_scoped_device_info(
            device_info,
            scoped_identifier=scoped_identifier,
            via_device=via_device,
        )

    instance = payload.get("ha_device_instance")
    if isinstance(instance, MutableMapping):
        instance[IDENTITY_SCOPE_KEY] = scope
        instance_device_info = instance.get("device_info")
        if isinstance(instance_device_info, MutableMapping):
            _apply_scoped_device_info(
                instance_device_info,
                scoped_identifier=scoped_identifier,
                via_device=via_device,
            )


def scoped_device_identifier(scope: str, device_id: Any) -> str:
    """Return the scoped HA device identifier value for a source device."""
    return f"{_safe_part(scope)}:device:{_safe_part(device_id)}"


def scoped_house_identifier(scope: str, house_id: Any) -> str:
    """Return the scoped HA device identifier value for a house helper device."""
    return f"{_safe_part(scope)}:house:{_safe_part(house_id) or '0'}"


def _apply_scoped_device_info(
    device_info: MutableMapping[str, Any],
    *,
    scoped_identifier: list[str],
    via_device: list[str] | None,
) -> None:
    device_info["identifiers"] = [scoped_identifier]
    if via_device is not None:
        device_info["via_device"] = via_device


def _scoped_via_device(
    payload: Mapping[str, Any],
    scope: str,
) -> list[str] | None:
    device_info = payload.get("device_info")
    raw_via = device_info.get("via_device") if isinstance(device_info, Mapping) else None
    if not isinstance(raw_via, (list, tuple)) or len(raw_via) != 2:
        return None
    via_identifier = to_str(raw_via[1])
    if not via_identifier:
        return None
    via_device_id = via_identifier.rsplit(":", 1)[-1]
    return [DOMAIN, scoped_device_identifier(scope, via_device_id)]


def _source_device_id(payload: Mapping[str, Any]) -> str | None:
    for key in ("device_id", "id", "deviceId", "did"):
        if value := to_str(payload.get(key)):
            return value
    return None


def _fingerprint(value: Any) -> str:
    text = to_str(value) or "unknown"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _safe_part(value: Any) -> str:
    text = to_str(value) or ""
    text = _ID_PART_RE.sub("_", text.strip()).strip("_").lower()
    return text or "unknown"


__all__ = [
    "IDENTITY_SCOPE_KEY",
    "apply_identity_scope_to_device_maps",
    "apply_identity_scope_to_device_payload",
    "coordinator_identity_scope",
    "device_entity_unique_id",
    "entity_unique_id",
    "entity_unique_id_prefix",
    "entry_identity_scope",
    "payload_entity_unique_id_prefix",
    "scoped_device_identifier",
    "scoped_entity_unique_id",
    "scoped_house_identifier",
]
