"""Yeelight Pro select entity tests."""

from __future__ import annotations

from custom_components.yeelight_pro.select import (
    NAME_GROUP,
    NAME_ROOM,
    NAME_SCENE,
    YeelightProGroupSelect,
    YeelightProRoomSelect,
    YeelightProSceneSelect,
)


def test_house_select_entities_have_friendly_names(mock_coordinator) -> None:
    """固定家庭选择器实体必须直接提供用户友好名称."""
    room = YeelightProRoomSelect(mock_coordinator, [{"id": "1", "name": "客厅"}])
    group = YeelightProGroupSelect(mock_coordinator, [{"id": "2", "name": "客厅灯组"}])
    scene = YeelightProSceneSelect(mock_coordinator, [{"id": "3", "name": "回家模式"}])

    assert room.name == NAME_ROOM
    assert group.name == NAME_GROUP
    assert scene.name == NAME_SCENE
