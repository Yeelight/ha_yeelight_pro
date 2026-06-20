"""Redacted report sample helpers for private-house coverage audits."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from custom_components.yeelight_pro.utils import to_str
from scripts.private_house_audit.projection import (
    safe_param_keys,
    schema_gap_reason,
    stable_digest,
)


def candidate_samples(
    candidates: Sequence[Any], *, limit: int = 24
) -> list[dict[str, Any]]:
    """Return redacted expected/missing entity candidate samples."""
    samples = []
    for candidate in candidates[:limit]:
        samples.append({
            "platform": candidate.platform,
            "component_id": candidate.component_id,
            "name": candidate.name,
            "entity_category": candidate.entity_category or "primary",
            "role": candidate_role(candidate),
            "unique_id_hash": stable_digest(candidate.unique_id),
        })
    return samples


def source_evidence(
    payload: Mapping[str, Any],
    inventory: Mapping[str, Any],
) -> dict[str, Any]:
    """Return redacted source facts used to justify coverage conclusions."""
    raw_properties = _property_rows(payload.get("properties"))
    value_stats = _property_value_stats(raw_properties)
    subdevices = [
        item for item in payload.get("subDeviceList") or [] if isinstance(item, Mapping)
    ]
    subdevice_property_keys: list[str] = []
    for subdevice in subdevices:
        index = to_str(subdevice.get("index")) or ""
        for prop in _property_rows(subdevice.get("properties")):
            prop_id = _property_id(prop)
            if not prop_id:
                continue
            subdevice_property_keys.append(
                f"{index}-{prop_id}" if index else str(prop_id)
            )
    params = payload.get("params")
    return {
        "raw_property_count": len(raw_properties),
        "raw_property_keys": _bounded_sorted(_property_id(prop) for prop in raw_properties),
        "raw_property_value_count": value_stats["value_count"],
        "raw_property_empty_count": value_stats["empty_count"],
        "raw_property_value_fields": value_stats["value_fields"],
        "subdevice_count": len(subdevices),
        "subdevice_property_count": len(subdevice_property_keys),
        "subdevice_property_keys": _bounded_sorted(subdevice_property_keys),
        "params_count": len(params) if isinstance(params, Mapping) else 0,
        "param_keys": safe_param_keys(payload),
        "product_schema_available": isinstance(payload.get("product_schema"), Mapping),
        "product_model_available": isinstance(payload.get("ha_product_model"), Mapping),
        "device_instance_available": isinstance(payload.get("ha_device_instance"), Mapping),
        "model_components_count": int(inventory.get("model_components_count") or 0),
        "model_properties_count": int(inventory.get("model_properties_count") or 0),
        "model_events_count": int(inventory.get("model_events_count") or 0),
        "schema_gap_reason": schema_gap_reason(payload) or "",
    }


def registry_samples(
    registry_rows: Sequence[Mapping[str, Any]] | Any,
    *,
    limit: int = 24,
) -> list[dict[str, Any]]:
    """Return redacted stale registry row samples for device-level diagnosis."""
    samples: list[dict[str, Any]] = []
    for row in registry_rows:
        if not isinstance(row, Mapping):
            continue
        unique_id = to_str(row.get("unique_id"))
        samples.append({
            "platform": entity_domain(row),
            "component_id": _component_id_from_unique_id(unique_id),
            "name": to_str(row.get("original_name"))
            or to_str(row.get("object_id_base")),
            "entity_category": to_str(row.get("entity_category")) or "primary",
            "role": actual_row_role(row),
            "unique_id_hash": stable_digest(unique_id),
        })
        if len(samples) >= limit:
            break
    return samples


def entity_domain(row: Mapping[str, Any]) -> str:
    """Return HA entity domain from the registry entity_id."""
    entity_id = to_str(row.get("entity_id"))
    if not entity_id or "." not in entity_id:
        return ""
    return entity_id.split(".", 1)[0]


def candidate_role(candidate: Any) -> str:
    """Return a user-facing coverage role for an expected entity candidate."""
    if getattr(candidate, "platform", None) == "event":
        return "event"
    category = getattr(candidate, "entity_category", None)
    if category == "config":
        return "config"
    if category == "diagnostic":
        return "diagnostic"
    return "primary_control_or_state"


def actual_row_role(row: Mapping[str, Any]) -> str:
    """Return a user-facing coverage role for one HA registry row."""
    if entity_domain(row) == "event":
        return "event"
    category = to_str(row.get("entity_category"))
    if category == "config":
        return "config"
    if category == "diagnostic":
        return "diagnostic"
    return "primary_control_or_state"


def _property_rows(value: Any) -> list[Mapping[str, Any]]:
    """Return Open API property mappings without exposing values."""
    return [item for item in value or [] if isinstance(item, Mapping)]


def _property_id(prop: Mapping[str, Any]) -> str:
    """Return a redacted property id from Open API property row variants."""
    return to_str(prop.get("propId", prop.get("propName"))) or ""


def _property_value_stats(properties: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return redacted value-presence stats for Open API property rows."""
    value_count = 0
    empty_count = 0
    value_fields: set[str] = set()
    for prop in properties:
        field = _property_value_field(prop)
        if field:
            value_fields.add(field)
            if prop.get(field) is None:
                empty_count += 1
            else:
                value_count += 1
            continue
        empty_count += 1
    return {
        "value_count": value_count,
        "empty_count": empty_count,
        "value_fields": sorted(value_fields),
    }


def _property_value_field(prop: Mapping[str, Any]) -> str:
    """Return the supported value field present in one property row."""
    if "value" in prop:
        return "value"
    if "data" in prop:
        return "data"
    return ""


def _bounded_sorted(values: Any, *, limit: int = 24) -> list[str]:
    """Return stable bounded non-empty text values."""
    return sorted({str(value) for value in values if value})[:limit]


def _component_id_from_unique_id(unique_id: str) -> str:
    """Best-effort component id guess from Yeelight entity unique_id."""
    if not unique_id:
        return ""
    marker = "_device_"
    if marker not in unique_id:
        return ""
    tail = unique_id.split(marker, 1)[1].split("_", 1)
    if len(tail) != 2:
        return ""
    return tail[1]
