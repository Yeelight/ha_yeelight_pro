"""Scene row compatibility tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.yeelight_pro.button import (
    YeelightProSceneButton,
    _iter_button_entities,
)
from custom_components.yeelight_pro.identity import entry_identity_scope, scoped_entity_unique_id


def test_scene_buttons_accept_scene_id_alias() -> None:
    """云端情景按钮应兼容 Open API 的 sceneId/sceneName 字段。"""
    coordinator = MagicMock()
    coordinator.entry_data = {}
    coordinator.house_id = 0
    coordinator.scenes = [
        {"sceneId": "scene_2", "sceneName": "离家", "icon": "scene_1"},
        {"scene_id": "scene_3", "name": "观影"},
        {"name": "缺少 ID"},
    ]

    entities = _iter_button_entities(coordinator)

    scope = entry_identity_scope({}, 0)
    assert [entity.unique_id for entity in entities] == [
        scoped_entity_unique_id(scope, "scene", "scene_2"),
        scoped_entity_unique_id(scope, "scene", "scene_3"),
    ]
    assert [entity.name for entity in entities] == ["离家", "观影"]


@pytest.mark.asyncio
async def test_scene_button_executes_scene_id_alias() -> None:
    """场景按钮执行时应使用 sceneId，而不是只依赖 id 字段。"""
    coordinator = MagicMock()
    coordinator.entry_data = {}
    coordinator.house_id = 0
    coordinator.async_execute_scene = AsyncMock()
    button = YeelightProSceneButton(
        coordinator,
        {"sceneId": "scene_2", "sceneName": "离家"},
    )

    await button.async_press()

    scope = entry_identity_scope({}, 0)
    assert button.unique_id == scoped_entity_unique_id(scope, "scene", "scene_2")
    assert button.name == "离家"
    coordinator.async_execute_scene.assert_awaited_once_with("scene_2")
