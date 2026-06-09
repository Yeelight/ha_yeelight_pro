"""Yeelight IoT registry protocol and Open API node-type tests."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.capabilities import connection_protocol, node_type


@pytest.mark.parametrize(
    ("source", "protocol_id", "key", "bridge"),
    [
        ("不连接", -1, "none", False),
        (0, 0, "direct", False),
        ("mesh协议", 1, "mesh", True),
        ("matter", 2, "matter", True),
        ("dali协议", 3, "dali", True),
        ("thread", 4, "thread", True),
    ],
)
def test_connection_protocols_are_metadata(
    source: object,
    protocol_id: int,
    key: str,
    bridge: bool,
) -> None:
    """连接协议是产品/桥接元数据，不是 HA 平台."""
    protocol = connection_protocol(source)

    assert protocol is not None
    assert protocol.protocol_id == protocol_id
    assert protocol.key == key
    assert protocol.bridge_protocol is bridge


def test_open_platform_node_types_are_registered() -> None:
    """open platform nodeType 必须显式表达控制路径维度."""
    assert node_type("room") == 1
    assert node_type("device") == 2
    assert node_type("area") == 3
    assert node_type("group") == 4
    assert node_type("house") == 5
    assert node_type("scene") is None
