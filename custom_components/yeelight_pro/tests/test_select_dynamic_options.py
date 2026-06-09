"""Select 平台动态选项测试."""

import traceback

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.select import (
    EMPTY_OPTION,
    ERROR_UNKNOWN_GROUP_OPTION,
    ERROR_UNKNOWN_ROOM_OPTION,
    ERROR_UNKNOWN_SCENE_OPTION,
    YeelightProGroupSelect,
    YeelightProRoomSelect,
    YeelightProSceneSelect,
)


SENSITIVE_OPTION = "secret-token https://api.yeelight.com 房间 12345"


def _disable_state_write(entity) -> None:
    """直接实例化实体时跳过 Home Assistant 状态写入."""
    entity.async_write_ha_state = lambda: None


def _assert_input_not_echoed(error: HomeAssistantError, *, expected: str) -> None:
    """断言错误和 traceback 不回显用户输入的选项值."""
    message = str(error)
    formatted = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )

    assert expected in message
    assert SENSITIVE_OPTION not in message
    assert SENSITIVE_OPTION not in formatted


@pytest.mark.asyncio
async def test_room_select_uses_latest_coordinator_rooms(mock_coordinator) -> None:
    """房间选项和当前值必须跟随 coordinator.rooms 更新."""
    mock_coordinator.rooms = [
        {"id": "room_1", "name": "客厅"},
        {"id": "room_2", "name": "卧室"},
    ]
    select = YeelightProRoomSelect(mock_coordinator, mock_coordinator.rooms)
    _disable_state_write(select)

    assert select.options == ["客厅", "卧室"]
    assert select.current_option == "客厅"

    await select.async_select_option("卧室")
    assert select.current_option == "卧室"

    mock_coordinator.rooms = [
        {"id": "room_3", "name": "书房"},
    ]
    assert select.options == ["书房"]
    assert select.current_option is None

    await select.async_select_option("书房")
    assert select.current_option == "书房"

    mock_coordinator.rooms = []
    assert select.options == [EMPTY_OPTION]
    assert select.current_option is None


@pytest.mark.asyncio
async def test_room_select_rejects_unknown_option(mock_coordinator) -> None:
    """未知房间选项必须向 HA 调用方报告失败."""
    mock_coordinator.rooms = [
        {"id": "room_1", "name": "客厅"},
    ]
    select = YeelightProRoomSelect(mock_coordinator, mock_coordinator.rooms)
    _disable_state_write(select)

    with pytest.raises(HomeAssistantError) as exc_info:
        await select.async_select_option(SENSITIVE_OPTION)

    _assert_input_not_echoed(exc_info.value, expected=ERROR_UNKNOWN_ROOM_OPTION)
    assert select.current_option == "客厅"


@pytest.mark.asyncio
async def test_group_select_uses_latest_coordinator_groups(mock_coordinator) -> None:
    """灯组选项和当前值必须跟随 coordinator.groups 更新."""
    mock_coordinator.groups = [
        {"id": "group_1", "name": "一楼灯组"},
        {"id": "group_2", "name": "二楼灯组"},
    ]
    select = YeelightProGroupSelect(mock_coordinator, mock_coordinator.groups)
    _disable_state_write(select)

    assert select.options == ["一楼灯组", "二楼灯组"]
    assert select.current_option == "一楼灯组"

    await select.async_select_option("二楼灯组")
    assert select.current_option == "二楼灯组"

    mock_coordinator.groups = [
        {"id": "group_3", "name": "地下室灯组"},
    ]
    assert select.options == ["地下室灯组"]
    assert select.current_option is None

    await select.async_select_option("地下室灯组")
    assert select.current_option == "地下室灯组"

    mock_coordinator.groups = []
    assert select.options == [EMPTY_OPTION]
    assert select.current_option is None


@pytest.mark.asyncio
async def test_group_select_rejects_unknown_option(mock_coordinator) -> None:
    """未知灯组选项必须向 HA 调用方报告失败."""
    mock_coordinator.groups = [
        {"id": "group_1", "name": "一楼灯组"},
    ]
    select = YeelightProGroupSelect(mock_coordinator, mock_coordinator.groups)
    _disable_state_write(select)

    with pytest.raises(HomeAssistantError) as exc_info:
        await select.async_select_option(SENSITIVE_OPTION)

    _assert_input_not_echoed(exc_info.value, expected=ERROR_UNKNOWN_GROUP_OPTION)
    assert select.current_option == "一楼灯组"


@pytest.mark.asyncio
async def test_scene_select_uses_latest_coordinator_scenes(mock_coordinator) -> None:
    """场景选项和最后执行值必须跟随 coordinator.scenes 更新."""
    mock_coordinator.scenes = [
        {"id": "scene_1", "name": "回家"},
        {"id": "scene_2", "name": "离家"},
    ]
    select = YeelightProSceneSelect(mock_coordinator, mock_coordinator.scenes)
    _disable_state_write(select)

    assert select.options == ["回家", "离家"]
    assert select.current_option is None

    await select.async_select_option("离家")
    mock_coordinator.async_execute_scene.assert_awaited_once_with("scene_2")
    assert select.current_option == "离家"

    mock_coordinator.scenes = [
        {"id": "scene_3", "name": "观影"},
    ]
    assert select.options == ["观影"]
    assert select.current_option is None

    await select.async_select_option("观影")
    mock_coordinator.async_execute_scene.assert_awaited_with("scene_3")
    assert select.current_option == "观影"

    mock_coordinator.scenes = []
    assert select.options == [EMPTY_OPTION]
    assert select.current_option is None


@pytest.mark.asyncio
async def test_scene_select_rejects_unknown_option_without_echoing_input(
    mock_coordinator,
) -> None:
    """未知场景选项错误不能泄露用户输入的场景名称."""
    mock_coordinator.scenes = [
        {"id": "scene_1", "name": "回家"},
    ]
    select = YeelightProSceneSelect(mock_coordinator, mock_coordinator.scenes)
    _disable_state_write(select)

    with pytest.raises(HomeAssistantError) as exc_info:
        await select.async_select_option(SENSITIVE_OPTION)

    _assert_input_not_echoed(exc_info.value, expected=ERROR_UNKNOWN_SCENE_OPTION)
    mock_coordinator.async_execute_scene.assert_not_awaited()
