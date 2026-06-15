"""LAN endpoint method-family helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .lan_contract import LanMessageBuilder

LAN_ENDPOINT_GATEWAY = "gateway"
LAN_ENDPOINT_WIFI_PANEL = "wifi_panel"
LAN_WIFI_PANEL_PRODUCT_ID = 2
_UNSUPPORTED_WIFI_PANEL_ACK = {
    "result": "error",
    "data": {"reason": "unsupported_wifi_panel_request"},
}


def endpoint_kind_from_product_id(product_id: Any) -> str:
    """Map documented LAN discovery pid values to runtime method families."""
    try:
        return (
            LAN_ENDPOINT_WIFI_PANEL
            if int(product_id) == LAN_WIFI_PANEL_PRODUCT_ID
            else LAN_ENDPOINT_GATEWAY
        )
    except (TypeError, ValueError):
        return LAN_ENDPOINT_GATEWAY


def topology_message(builder: LanMessageBuilder, endpoint_kind: str) -> dict[str, Any]:
    """Build the topology request for one documented LAN endpoint family."""
    if endpoint_kind == LAN_ENDPOINT_WIFI_PANEL:
        return builder.device_get_topology()
    return builder.get_topology()


def set_properties_message(
    builder: LanMessageBuilder,
    endpoint_kind: str,
    nodes: list[Mapping[str, Any]],
    *,
    scenes: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a LAN write frame for the endpoint family or an error ACK."""
    if endpoint_kind == LAN_ENDPOINT_WIFI_PANEL:
        if scenes or any(node.get("nt") != 2 for node in nodes):
            return dict(_UNSUPPORTED_WIFI_PANEL_ACK)
        return builder.device_set_properties(nodes)
    return builder.set_properties(nodes, scenes=scenes)


__all__ = [
    "LAN_ENDPOINT_GATEWAY",
    "LAN_ENDPOINT_WIFI_PANEL",
    "LAN_WIFI_PANEL_PRODUCT_ID",
    "endpoint_kind_from_product_id",
    "set_properties_message",
    "topology_message",
]
