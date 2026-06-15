"""Merge LAN topology rows that describe one physical endpoint."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..utils import to_str


def merge_lan_payload(
    current: Mapping[str, Any] | None,
    incoming: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge LAN rows that share one documented physical node id."""
    if current is None:
        return dict(incoming)

    merged = dict(current)
    merged_category = _merged_category(current, incoming)
    merged["iot_category"] = merged_category
    merged["category"] = merged_category
    merged["effective_category"] = merged_category
    merged["type"] = merged_category
    merged["mixed_lan_types"] = True
    merged["lan_type"] = _merged_values(current.get("lan_type"), incoming.get("lan_type"))
    merged["model"] = _merged_label(current.get("model"), incoming.get("model"))
    merged["modelName"] = merged["model"]
    merged["productName"] = merged["model"]
    merged["model_id"] = _merged_label(current.get("model_id"), incoming.get("model_id"))
    merged["params"] = _merged_params(current.get("params"), incoming.get("params"))
    merged["subDeviceList"] = _merged_rows_by_identity(
        current.get("subDeviceList"),
        incoming.get("subDeviceList"),
        keys=("category", "index", "cid"),
    )
    merged["events"] = _merged_rows_by_identity(
        current.get("events"),
        incoming.get("events"),
        keys=("name", "id", "eventId"),
    )
    return merged


def _merged_params(first: Any, second: Any) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if isinstance(first, Mapping):
        params.update(dict(first))
    if isinstance(second, Mapping):
        params.update(dict(second))
    return params


def _merged_category(first: Mapping[str, Any], second: Mapping[str, Any]) -> str:
    """Return the primary category for a mixed LAN physical endpoint."""
    categories: set[str] = set()
    for item in (
        first.get("iot_category") or first.get("category"),
        second.get("iot_category") or second.get("category"),
    ):
        if category := to_str(item):
            categories.add(category)
    if categories & {"relay_switch", "switch"}:
        return "relay_switch"
    if len(categories) == 1:
        return next(iter(categories))
    return "other"


def _merged_rows_by_identity(
    first: Any,
    second: Any,
    *,
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in [*(_mapping_rows(first)), *(_mapping_rows(second))]:
        identity = tuple(item.get(key) for key in keys)
        if identity in seen:
            continue
        seen.add(identity)
        rows.append(dict(item))
    return rows


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _merged_values(first: Any, second: Any) -> list[Any]:
    values: list[Any] = []
    for value in (first, second):
        items = value if isinstance(value, list) else (value,)
        for item in items:
            if item is not None and item not in values:
                values.append(item)
    return values


def _merged_label(first: Any, second: Any) -> str:
    values = [to_str(item) for item in (first, second)]
    labels = [item for item in values if item]
    return " / ".join(dict.fromkeys(labels))


__all__ = ["merge_lan_payload"]
