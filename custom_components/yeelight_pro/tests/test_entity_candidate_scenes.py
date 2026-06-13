"""Entity candidate tests for Yeelight cloud scenes."""

from __future__ import annotations

from custom_components.yeelight_pro.entity_candidates import iter_entity_candidates
from custom_components.yeelight_pro.identity import entry_identity_scope, scoped_entity_unique_id

from .test_entity_candidates import _Coordinator


def test_entity_candidates_project_cloud_scenes_as_buttons_only() -> None:
    """云端情景是远端动作，只生成 button，不再冒充 HA 原生 scene."""
    coordinator = _Coordinator(
        data={},
        scenes=[{"sceneId": "same_scene", "sceneName": "回家"}],
    )
    candidates = list(iter_entity_candidates(coordinator))

    scene_uid = scoped_entity_unique_id(entry_identity_scope({}, 0), "scene", "same_scene")
    assert [(item.platform, item.unique_id) for item in candidates] == [
        ("button", scene_uid),
    ]
    assert candidates[0].name == "回家"
    assert candidates[0].icon == "mdi:palette"
    assert {item.key for item in candidates} == {
        ("button", scene_uid),
    }


def test_entity_candidates_use_friendly_scene_fallback_name() -> None:
    """无名称的云端情景按钮也应使用中文情景 fallback，不暴露 raw platform."""
    coordinator = _Coordinator(data={}, scenes=[{"id": "scene_1"}])
    candidates = list(iter_entity_candidates(coordinator))

    assert len(candidates) == 1
    assert candidates[0].platform == "button"
    assert candidates[0].name == "情景 scene_1"
