"""Topology node metadata helpers for Yeelight Pro house-level entities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .identity import scoped_entity_unique_id
from .utils import to_str

NODE_LIGHT_KINDS = ("room", "area", "house")

_NODE_COLLECTIONS = {
    "room": "rooms",
    "area": "areas",
    "house": "houses",
}
_NODE_ID_KEYS = {
    "room": ("id", "roomId", "room_id"),
    "area": ("id", "areaId", "area_id", "groupId", "group_id"),
    "house": ("id", "houseId", "house_id", "projectId", "project_id"),
}
_NODE_NAME_KEYS = {
    "room": ("name", "roomName", "room_name", "n"),
    "area": ("name", "areaName", "area_name", "groupName", "group_name", "n"),
    "house": ("name", "houseName", "house_name", "projectName", "project_name", "n"),
}
_NODE_LABELS = {
    "room": "房间",
    "area": "区域",
    "house": "整屋",
}
_NODE_ICONS = {
    "room": "mdi:floor-plan",
    "area": "mdi:select-group",
    "house": "mdi:home-lightbulb",
}


def iter_topology_node_rows(coordinator: Any, node_kind: str) -> Iterable[Mapping[str, Any]]:
    """Return cached topology rows for one supported node kind."""
    collection = _NODE_COLLECTIONS.get(node_kind)
    if collection is None:
        return ()
    rows = getattr(coordinator, collection, None)
    if not isinstance(rows, list):
        return ()
    return (row for row in rows if isinstance(row, Mapping))


def topology_node_id(row: Mapping[str, Any], node_kind: str) -> str | None:
    """Return the stable source id for a topology node row."""
    for key in _NODE_ID_KEYS.get(node_kind, ("id",)):
        value = _text(row.get(key))
        if value is not None:
            return value
    return None


def topology_node_name(
    row: Mapping[str, Any],
    node_kind: str,
    node_id: str,
) -> str:
    """Return a user-facing topology node name."""
    for key in _NODE_NAME_KEYS.get(node_kind, ("name",)):
        value = _text(row.get(key))
        if value is not None:
            return value
    return f"{node_kind_label(node_kind)} {node_id}"


def topology_node_params(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact propName -> value map from node params/properties."""
    params = row.get("params")
    if isinstance(params, Mapping):
        return dict(params)

    properties = row.get("properties")
    if isinstance(properties, Mapping):
        return dict(properties)
    if isinstance(properties, list):
        parsed: dict[str, Any] = {}
        for item in properties:
            if not isinstance(item, Mapping):
                continue
            name = _property_name(item)
            if name is None:
                continue
            parsed[name] = _property_value(item)
        return parsed
    return {}


def node_light_unique_id(scope: str, node_kind: str, node_id: str) -> str:
    """Return the scoped HA unique_id for a topology node light."""
    return scoped_entity_unique_id(scope, node_kind, node_id, "light")


def node_kind_label(node_kind: str) -> str:
    """Return the Chinese display label for a topology node kind."""
    return _NODE_LABELS.get(node_kind, node_kind)


def node_kind_icon(node_kind: str) -> str:
    """Return the icon for a topology node light."""
    return _NODE_ICONS.get(node_kind, "mdi:home-lightbulb")


def _property_name(item: Mapping[str, Any]) -> str | None:
    """Return a property id from OpenAPI property metadata."""
    for key in ("propName", "propId", "prop_id", "name"):
        if value := _text(item.get(key)):
            return value
    return None


def _property_value(item: Mapping[str, Any]) -> Any:
    """Return a property value from OpenAPI property metadata."""
    for key in ("value", "propertyValue", "property_value", "val"):
        if key in item:
            return item[key]
    return None


def _text(value: Any) -> str | None:
    text = to_str(value)
    return text or None


__all__ = [
    "NODE_LIGHT_KINDS",
    "iter_topology_node_rows",
    "node_kind_icon",
    "node_kind_label",
    "node_light_unique_id",
    "topology_node_id",
    "topology_node_name",
    "topology_node_params",
]
