"""Node identity helpers for private subscribe-snapshot diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from custom_components.yeelight_pro.push import NODE_ID_ALIAS_KEYS, TOPOLOGY_NODE_ID_ALIAS_KEYS
from custom_components.yeelight_pro.utils import to_int

_IDENTITY_FIELDS = frozenset(NODE_ID_ALIAS_KEYS)



def _identity_candidate_fields(candidates: tuple[tuple[str, int], ...]) -> list[str]:
    """Return identity alias fields without values."""
    fields: list[str] = []
    for field, _value in candidates:
        if field in _IDENTITY_FIELDS and field not in fields:
            fields.append(field)
    return fields


def _node_id_candidates(device: Mapping[str, Any]) -> tuple[tuple[str, int], ...]:
    """Return snapshot node id aliases in production parser priority order."""
    candidates: list[tuple[str, int]] = []
    for key in (*NODE_ID_ALIAS_KEYS, *TOPOLOGY_NODE_ID_ALIAS_KEYS):
        node_id = to_int(device.get(key))
        if node_id is not None:
            candidates.append((key, node_id))
    return tuple(candidates)


def _node_type(device: Mapping[str, Any]) -> int | None:
    """Return documented node type aliases from a snapshot row."""
    for key in ("nt", "nodeType", "node_type"):
        node_type = to_int(device.get(key))
        if node_type is not None:
            return node_type
    return None

__all__ = ["_IDENTITY_FIELDS", "_identity_candidate_fields", "_node_id_candidates", "_node_type"]
