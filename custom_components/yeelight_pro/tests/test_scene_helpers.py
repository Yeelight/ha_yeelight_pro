"""Scene row compatibility tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.yeelight_pro.button import (
    YeelightProSceneButton,
    _iter_button_entities,
)
from custom_components.yeelight_pro.const import DEFAULT_HOUSE_NAME, DOMAIN
from custom_components.yeelight_pro.identity import (
    entry_identity_scope,
    scoped_entity_unique_id,
    scoped_house_identifier,
)


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


def test_scene_button_uses_house_device_info_when_gateways_exist() -> None:
    """场景按钮属于家庭级动作，不应透传网关 raw device_info。"""
    coordinator = MagicMock()
    coordinator.entry_data = {}
    coordinator.house_id = 42
    coordinator.houses = []
    coordinator.get_gateway_devices.return_value = {
        1: {
            "ha_device_instance": {
                "device_info": {
                    "default_name": "gateway-DALI网关-17000001-01",
                    "identifiers": [[DOMAIN, "private:device:50018326"]],
                    "manufacturer": "Yeelight",
                    "model": "DALI网关",
                    "model_id": "YL-17000001",
                    "name": "gateway-DALI网关-17000001-01",
                }
            }
        }
    }
    button = YeelightProSceneButton(
        coordinator,
        {"sceneId": "scene_2", "sceneName": "离家"},
    )

    device_info = button.device_info

    scope = entry_identity_scope({}, 42)
    assert device_info == {
        "identifiers": {(DOMAIN, scoped_house_identifier(scope, 42))},
        "manufacturer": "Yeelight",
        "model": "Yeelight Pro 家庭",
        "name": f"{DEFAULT_HOUSE_NAME} 场景",
    }
    assert "default_name" not in device_info
