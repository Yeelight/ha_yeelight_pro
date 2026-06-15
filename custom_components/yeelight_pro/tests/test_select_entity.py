"""Yeelight Pro select entity tests."""

from __future__ import annotations

from custom_components.yeelight_pro.select import (
    YeelightProGroupSelect,
    YeelightProRoomSelect,
    YeelightProSceneSelect,
)


def test_house_select_entities_use_translation_keys(mock_coordinator) -> None:
    """固定家庭选择器实体名称必须交给 HA 翻译层处理。"""
    room = YeelightProRoomSelect(mock_coordinator, [{"id": "1", "name": "客厅"}])
    group = YeelightProGroupSelect(mock_coordinator, [{"id": "2", "name": "客厅灯组"}])
    scene = YeelightProSceneSelect(mock_coordinator, [{"id": "3", "name": "回家模式"}])

    assert "__attr_name" not in vars(room)
    assert "__attr_name" not in vars(group)
    assert "__attr_name" not in vars(scene)
    assert room.translation_key == "active_room"
    assert group.translation_key == "active_group"
    assert scene.translation_key == "active_scene"
