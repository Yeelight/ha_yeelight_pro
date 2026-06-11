"""Scene row compatibility tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.yeelight_pro.button import (
    YeelightProSceneButton,
    _iter_button_entities,
)


def test_scene_buttons_accept_scene_id_alias() -> None:
    """云端情景按钮应兼容 Open API 的 sceneId/sceneName 字段。"""
    coordinator = MagicMock()
    coordinator.scenes = [
        {"sceneId": "scene_2", "sceneName": "离家", "icon": "scene_1"},
        {"scene_id": "scene_3", "name": "观影"},
        {"name": "缺少 ID"},
    ]

    entities = _iter_button_entities(coordinator)

    assert [entity.unique_id for entity in entities] == [
        "yeelight_pro_scene_scene_2",
        "yeelight_pro_scene_scene_3",
    ]
    assert [entity.name for entity in entities] == ["离家", "观影"]


@pytest.mark.asyncio
async def test_scene_button_executes_scene_id_alias() -> None:
    """场景按钮执行时应使用 sceneId，而不是只依赖 id 字段。"""
    coordinator = MagicMock()
    coordinator.async_execute_scene = AsyncMock()
    button = YeelightProSceneButton(
        coordinator,
        {"sceneId": "scene_2", "sceneName": "离家"},
    )

    await button.async_press()

    assert button.unique_id == "yeelight_pro_scene_scene_2"
    assert button.name == "离家"
    coordinator.async_execute_scene.assert_awaited_once_with("scene_2")
