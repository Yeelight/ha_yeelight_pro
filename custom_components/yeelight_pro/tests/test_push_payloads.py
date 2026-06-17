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
