"""Yeelight Pro LAN method constants shared by contract and payload adapters."""
from __future__ import annotations

# 网关方法（pid=1 Mesh 网关）
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

# WiFi 全面屏设备方法（pid=2）
METHOD_DEVICE_GET_TOPOLOGY = "device_get.topology"
METHOD_DEVICE_GET_NODE = "device_get.node"
METHOD_DEVICE_SET_PROP = "device_set.prop"
METHOD_DEVICE_POST_TOPOLOGY = "getway_post.topology"  # 协议文档中的拼写
METHOD_DEVICE_POST_PROP = "device_post.prop"
METHOD_DEVICE_POST_EVENT = "device_post.event"

# 全面屏发现广播消息
LAN_DEVICE_DISCOVERY_MESSAGE = "YEELIGHT_DEVICE_CONTROL_DISCOVER"

# 所有推送方法（网关 + 全面屏）
ALL_POST_METHODS = {
    METHOD_POST_TOPOLOGY,
    METHOD_POST_PROP,
    METHOD_POST_EVENT,
    METHOD_DEVICE_POST_TOPOLOGY,
    METHOD_DEVICE_POST_PROP,
    METHOD_DEVICE_POST_EVENT,
}

__all__ = [
    "ALL_POST_METHODS",
    "LAN_DEVICE_DISCOVERY_MESSAGE",
    "METHOD_DEVICE_GET_NODE",
    "METHOD_DEVICE_GET_TOPOLOGY",
    "METHOD_DEVICE_POST_EVENT",
    "METHOD_DEVICE_POST_PROP",
    "METHOD_DEVICE_POST_TOPOLOGY",
    "METHOD_DEVICE_SET_PROP",
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
