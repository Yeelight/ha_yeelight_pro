"""Yeelight Pro LAN method constants shared by contract and payload adapters."""
from __future__ import annotations

METHOD_GET_TOPOLOGY = "gateway_get.topology"
METHOD_GET_NODE = "gateway_get.node"
METHOD_GET_GROUP = "gateway_get.group"
METHOD_GET_ROOM = "gateway_get.room"
METHOD_GET_SCENE = "gateway_get.scene"
METHOD_SET_PROP = "gateway_set.prop"
METHOD_SET_EVENT = "gateway_set.event"
METHOD_POST_TOPOLOGY = "gateway_post.topology"
METHOD_POST_PROP = "gateway_post.prop"
METHOD_POST_EVENT = "gateway_post.event"

__all__ = [
    "METHOD_GET_GROUP",
    "METHOD_GET_NODE",
    "METHOD_GET_ROOM",
    "METHOD_GET_SCENE",
    "METHOD_GET_TOPOLOGY",
    "METHOD_POST_EVENT",
    "METHOD_POST_PROP",
    "METHOD_POST_TOPOLOGY",
    "METHOD_SET_EVENT",
    "METHOD_SET_PROP",
]
