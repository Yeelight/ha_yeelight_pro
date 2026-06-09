"""No-network helpers for the Yeelight Pro LAN gateway protocol contract."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .lan_methods import (
    METHOD_GET_GROUP,
    METHOD_GET_NODE,
    METHOD_GET_ROOM,
    METHOD_GET_SCENE,
    METHOD_GET_TOPOLOGY,
    METHOD_POST_EVENT,
    METHOD_POST_PROP,
    METHOD_POST_TOPOLOGY,
    METHOD_SET_EVENT,
    METHOD_SET_PROP,
)

LAN_DISCOVERY_MESSAGE = "YEELIGHT_GATEWAY_CONTROL_DISCOVER"
LAN_DISCOVERY_PORT = 1982
LAN_GATEWAY_PORT = 65443
LAN_PROTOCOL_VERSION = "1.0"
LAN_FRAME_SEPARATOR = "\r\n"


@dataclass(frozen=True, slots=True)
class LanDiscoveryResponse:
    """Parsed Yeelight Pro LAN discovery response."""

    product_id: int
    mac: str
    device_id: str
    ip: str


@dataclass(slots=True)
class LanMessageBuilder:
    """Build Yeelight Pro LAN JSON messages with monotonically increasing ids."""

    _next_id: int = field(default=1)

    def get_topology(self) -> dict[str, Any]:
        """Build a gateway topology request."""
        return build_get_topology_message(self._claim_id())

    def get_node(self, node_id: int = 0) -> dict[str, Any]:
        """Build a node detail request."""
        return build_get_node_message(self._claim_id(), node_id=node_id)

    def get_group(self, group_id: int = 0) -> dict[str, Any]:
        """Build a Mesh group detail request."""
        return build_get_group_message(self._claim_id(), group_id=group_id)

    def get_room(self, room_id: int = 0) -> dict[str, Any]:
        """Build a room detail request."""
        return build_get_room_message(self._claim_id(), room_id=room_id)

    def get_scene(self, scene_id: int = 0) -> dict[str, Any]:
        """Build a scene detail request."""
        return build_get_scene_message(self._claim_id(), scene_id=scene_id)

    def set_properties(
        self,
        nodes: list[Mapping[str, Any]],
        *,
        scenes: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build a LAN property-control request without I/O."""
        return build_set_properties_message(
            self._claim_id(),
            nodes=nodes,
            scenes=scenes,
        )

    def _claim_id(self) -> int:
        """Return current id and advance the internal counter."""
        message_id = self._next_id
        self._next_id += 1
        return message_id


def parse_discovery_response(text: str) -> LanDiscoveryResponse:
    """Parse the UDP discovery response documented by the local protocol."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = key.strip().casefold()
        value = value.strip()
        if key and value:
            fields[key] = value

    try:
        product_id = int(fields["pid"])
        mac = fields["mac"]
        device_id = fields["did"]
        ip = fields["ip"]
    except (KeyError, ValueError) as err:
        raise ValueError("Invalid Yeelight Pro LAN discovery response") from err

    return LanDiscoveryResponse(
        product_id=product_id,
        mac=mac,
        device_id=device_id,
        ip=ip,
    )


def encode_lan_frame(message: Mapping[str, Any]) -> bytes:
    """Encode one JSON LAN message with the documented CRLF separator."""
    return (
        json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        + LAN_FRAME_SEPARATOR
    ).encode("utf-8")


def decode_lan_frames(data: bytes | str) -> list[dict[str, Any]]:
    """Decode one or more CRLF-delimited LAN JSON frames."""
    text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
    frames: list[dict[str, Any]] = []
    for raw_frame in text.split(LAN_FRAME_SEPARATOR):
        raw_frame = raw_frame.strip()
        if not raw_frame:
            continue
        parsed = json.loads(raw_frame)
        if not isinstance(parsed, dict):
            raise ValueError("Yeelight Pro LAN frame must be a JSON object")
        frames.append(parsed)
    return frames


def build_get_topology_message(message_id: int) -> dict[str, Any]:
    """Build a gateway topology request."""
    return _base_message(message_id, METHOD_GET_TOPOLOGY)


def build_get_node_message(message_id: int, *, node_id: int = 0) -> dict[str, Any]:
    """Build a node detail request."""
    return _request_with_id(message_id, METHOD_GET_NODE, node_id)


def build_get_group_message(message_id: int, *, group_id: int = 0) -> dict[str, Any]:
    """Build a Mesh group detail request."""
    return _request_with_id(message_id, METHOD_GET_GROUP, group_id)


def build_get_room_message(message_id: int, *, room_id: int = 0) -> dict[str, Any]:
    """Build a room detail request."""
    return _request_with_id(message_id, METHOD_GET_ROOM, room_id)


def build_get_scene_message(message_id: int, *, scene_id: int = 0) -> dict[str, Any]:
    """Build a scene detail request."""
    return _request_with_id(message_id, METHOD_GET_SCENE, scene_id)


def build_set_properties_message(
    message_id: int,
    *,
    nodes: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a LAN property-control request."""
    if not nodes and not scenes:
        raise ValueError("Yeelight Pro LAN property request requires nodes or scenes")

    message = _base_message(message_id, METHOD_SET_PROP)
    if nodes:
        message["nodes"] = [dict(node) for node in nodes]
    if scenes:
        message["scenes"] = [dict(scene) for scene in scenes]
    return message


def is_lan_push_message(message: Mapping[str, Any]) -> bool:
    """Return whether a message is a gateway-to-client push frame."""
    return message.get("method") in {
        METHOD_POST_TOPOLOGY,
        METHOD_POST_PROP,
        METHOD_POST_EVENT,
    }


def _request_with_id(message_id: int, method: str, node_id: int) -> dict[str, Any]:
    """Build a LAN request whose params contain an id field."""
    message = _base_message(message_id, method)
    message["params"] = {"id": int(node_id)}
    return message


def _base_message(message_id: int, method: str) -> dict[str, Any]:
    """Build the shared LAN request envelope."""
    if int(message_id) <= 0:
        raise ValueError("Yeelight Pro LAN message id must be positive")
    return {
        "version": LAN_PROTOCOL_VERSION,
        "id": int(message_id),
        "method": method,
    }


from .lan_payload import (  # noqa: E402  # isort: skip
    YeelightLanPropertyUpdate,
    lan_event_payloads,
    lan_property_updates,
)


__all__ = [
    "LAN_DISCOVERY_MESSAGE",
    "LAN_DISCOVERY_PORT",
    "LAN_FRAME_SEPARATOR",
    "LAN_GATEWAY_PORT",
    "LAN_PROTOCOL_VERSION",
    "LanDiscoveryResponse",
    "LanMessageBuilder",
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
    "YeelightLanPropertyUpdate",
    "build_get_group_message",
    "build_get_node_message",
    "build_get_room_message",
    "build_get_scene_message",
    "build_get_topology_message",
    "build_set_properties_message",
    "decode_lan_frames",
    "encode_lan_frame",
    "is_lan_push_message",
    "lan_event_payloads",
    "lan_property_updates",
    "parse_discovery_response",
]
