"""Push property payload adapter tests."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError

import pytest

from custom_components.yeelight_pro.push import push_property_updates


def test_push_property_updates_normalize_open_platform_payload() -> None:
    """WebSocket prop payload 应先转换成本地状态覆盖，不直接耦合网络连接."""
    updates = push_property_updates(
        {
            "type": "prop",
            "msgId": "message-1",
            "nodes": [
                {
                    "id": 228215,
                    "nt": 2,
                    "params": {"p": True, "ct": 4500, "l": 100, "o": True},
                }
            ],
            "timestamp": 1724658984,
            "version": "1.0",
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228215
    assert updates[0].node_type == 2
    assert updates[0].params == {"p": True, "ct": 4500, "l": 100, "o": True}


def test_push_property_updates_do_not_fold_message_meta_into_state() -> None:
    """prop 消息元数据只用于传输追踪，不能混入设备状态 params."""
    updates = push_property_updates(
        {
            "type": "prop",
            "msgId": "message-secret",
            "nodes": [
                {
                    "id": 228215,
                    "nt": 2,
                    "componentId": "component-secret",
                    "roomName": "Room Secret",
                    "params": {"p": False},
                }
            ],
            "timestamp": 1724658984,
            "version": "1.0",
        }
    )

    assert len(updates) == 1
    assert updates[0].params == {"p": False}
    assert "message-secret" not in str(updates[0].params)
    assert "component-secret" not in str(updates[0].params)
    assert "Room Secret" not in str(updates[0].params)


def test_push_property_updates_accept_wrapped_data_payload() -> None:
    """部分 WebSocket transport 会把文档帧包在 data 内，状态仍应落地."""
    updates = push_property_updates(
        {
            "method": "message",
            "data": {
                "type": "prop",
                "msgId": "message-2",
                "nodes": [
                    {
                        "id": 228215,
                        "nt": 2,
                        "params": {"p": False},
                    }
                ],
            },
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228215
    assert updates[0].params == {"p": False}


def test_push_property_updates_accept_deeply_wrapped_private_payload() -> None:
    """私有部署多层 message/result/data envelope 不应退回 30 秒轮询."""
    updates = push_property_updates(
        {
            "method": "message",
            "result": {
                "code": 200,
                "data": {
                    "method": "gateway_post.prop",
                    "nodes": [
                        {
                            "id": 228225,
                            "nt": 2,
                            "params": {"1-p": False, "4-p": True},
                        }
                    ],
                },
            },
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228225
    assert updates[0].params == {"1-p": False, "4-p": True}


def test_push_property_updates_accept_gateway_post_prop_payload() -> None:
    """WebSocket 私有部署复用 gateway_post.prop 时也应即时更新状态。"""
    updates = push_property_updates(
        {
            "method": "gateway_post.prop",
            "nodes": [
                {
                    "id": 228225,
                    "nt": 2,
                    "o": True,
                    "params": {"1-p": False},
                }
            ],
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228225
    assert updates[0].node_type == 2
    assert updates[0].params == {"1-p": False, "o": True}


@pytest.mark.parametrize("wrapper_key", ["params", "result"])
def test_push_property_updates_accept_alternate_wrapped_payloads(
    wrapper_key: str,
) -> None:
    """私有部署可能把文档帧包在 params/result 内，状态不能被 transport 吞掉."""
    updates = push_property_updates(
        {
            "method": "message",
            wrapper_key: {
                "type": "prop",
                "nodes": [
                    {
                        "id": 228215,
                        "nt": 2,
                        "params": {"p": False},
                    }
                ],
            },
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228215
    assert updates[0].params == {"p": False}


def test_push_property_updates_accept_property_rows_and_top_level_online() -> None:
    """兼容属性列表形态和节点级 o，避免在线状态推送被丢弃."""
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 228216,
                    "nt": 2,
                    "o": True,
                    "properties": [
                        {"propId": "cp", "value": 66},
                        {"propName": "tp", "value": 80},
                    ],
                },
                {
                    "id": 228217,
                    "nt": 2,
                    "params": {"p": True},
                    "o": False,
                },
            ],
        }
    )

    assert [update.node_id for update in updates] == [228216, 228217]
    assert updates[0].params == {"cp": 66, "tp": 80, "o": True}
    assert updates[1].params == {"p": True, "o": False}


def test_push_property_updates_preserve_indexed_property_rows() -> None:
    """多通道属性行带 index 时必须保留为 N-prop，避免四键状态串路."""
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 228216,
                    "nt": 2,
                    "properties": [
                        {"propId": "sp", "index": 1, "value": True},
                        {"propId": "sp", "index": 2, "value": False},
                    ],
                }
            ],
        }
    )

    assert len(updates) == 1
    assert updates[0].params == {"1-sp": True, "2-sp": False}


def test_push_property_updates_accept_nested_data_property_rows() -> None:
    """兼容私有部署可能复用读属性 data 行数组的推送形态."""
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "resId": "228216",
                    "nt": 2,
                    "o": True,
                    "data": [
                        {"propId": "sp", "index": 1, "value": False},
                        {"propId": "sp", "index": 2, "value": True},
                    ],
                }
            ],
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228216
    assert updates[0].params == {"1-sp": False, "2-sp": True, "o": True}


def test_push_property_updates_accept_nested_single_data_property() -> None:
    """兼容节点 data 为单个 propId/value 对象的私有部署推送形态."""
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "resId": "228216",
                    "data": {"propId": "p", "value": True},
                }
            ],
        }
    )

    assert len(updates) == 1
    assert updates[0].params == {"p": True}


def test_push_property_updates_accept_online_only_node() -> None:
    """只推在线状态 o 的节点也必须刷新 HA 可用性。"""
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 228226,
                    "nt": 2,
                    "o": False,
                }
            ],
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228226
    assert updates[0].params == {"o": False}


def test_push_property_updates_accept_single_node_data_frame() -> None:
    """单节点 data frame 不应因缺少 nodes 数组导致 push manager 吞错误."""
    updates = push_property_updates(
        {
            "type": "prop",
            "id": 228218,
            "nt": 2,
            "propId": "p",
            "value": True,
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228218
    assert updates[0].params == {"p": True}


def test_push_property_updates_accept_node_id_aliases() -> None:
    """私有部署/读属性形态使用节点 ID 别名时也应更新目标设备."""
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "nodeId": "228219",
                    "nodeType": 4,
                    "params": {"p": True},
                },
                {
                    "resId": "228220",
                    "node_type": 1,
                    "properties": [{"propId": "cp", "value": 55}],
                },
                {
                    "deviceId": "228221",
                    "propName": "o",
                    "value": False,
                },
            ],
        }
    )

    assert [update.node_id for update in updates] == [228219, 228220, 228221]
    assert [update.node_type for update in updates] == [4, 1, None]
    assert updates[0].params == {"p": True}
    assert updates[1].params == {"cp": 55}
    assert updates[2].params == {"o": False}


def test_push_property_updates_accept_topology_node_id_aliases() -> None:
    """房间/区域/灯组等拓扑节点别名也应进入候选 ID，供运行时精确路由。"""
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": "998",
                    "groupId": "228230",
                    "roomId": "228231",
                    "areaId": "228232",
                    "houseId": "228233",
                    "projectId": "228234",
                    "params": {"p": True},
                }
            ],
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 998
    assert updates[0].node_id_candidates == (
        ("id", 998),
        ("groupId", 228230),
        ("roomId", 228231),
        ("areaId", 228232),
        ("houseId", 228233),
        ("projectId", 228234),
    )


def test_push_property_updates_scope_plain_params_with_component_index() -> None:
    """多组件 prop 帧带 index/key 时应转为官方 N-p/N-sp 键。"""
    updates = push_property_updates(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 228222,
                    "index": 2,
                    "params": {"p": False, "o": True},
                },
                {
                    "id": 228223,
                    "key": 3,
                    "params": {"sp": True},
                },
                {
                    "id": 228224,
                    "componentId": "relay_switch_4",
                    "propName": "p",
                    "value": True,
                },
            ],
        }
    )

    assert [update.node_id for update in updates] == [228222, 228223, 228224]
    assert updates[0].params == {"2-p": False, "o": True}
    assert updates[1].params == {"3-sp": True}
    assert updates[2].params == {"4-p": True}


def test_push_payload_rejects_invalid_nodes_shape() -> None:
    """无效 nodes 不应被静默当作空推送吞掉."""
    with pytest.raises(HomeAssistantError):
        push_property_updates({"type": "prop", "nodes": {"id": 1}})


def test_push_property_payload_rejects_invalid_node_items() -> None:
    """nodes 列表内的坏节点也必须显式报错，不能半吞推送帧."""
    with pytest.raises(HomeAssistantError):
        push_property_updates({"type": "prop", "nodes": [{"id": 1}, "bad-node"]})
