"""Dynamic entity device-import filter gate tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.dynamic_entities import async_track_dynamic_entities

from .dynamic_entity_helpers import (
    DummyEntity,
    coordinator_with_device_filter,
    entry_with_unload_hook,
    hass_with_state,
    patch_entity_registry,
    registry_entry,
)


def test_dynamic_entities_include_filter_blocks_unmatched_new_devices(
    monkeypatch,
) -> None:
    """include 过滤只允许匹配设备的新实体进入动态新增."""
    coordinator = coordinator_with_device_filter(
        {"enabled": True, "include": {"categories": ["light"]}}
    )
    coordinator.hass = hass_with_state(None)
    patch_entity_registry(monkeypatch, [])
    entry = entry_with_unload_hook()
    add_entities = MagicMock()

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [
            DummyEntity(f"{DOMAIN}_1_light", device_id=1),
            DummyEntity(f"{DOMAIN}_2_cover", device_id=2),
        ],
        logger=MagicMock(),
        platform_name="light",
    )

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_1_light"
    ]


def test_dynamic_entities_exclude_filter_blocks_matched_new_devices(
    monkeypatch,
) -> None:
    """exclude 过滤应阻止命中规则的新实体进入动态新增."""
    coordinator = coordinator_with_device_filter(
        {"enabled": True, "exclude": {"devices": ["2"]}}
    )
    coordinator.hass = hass_with_state(None)
    patch_entity_registry(monkeypatch, [])
    entry = entry_with_unload_hook()
    add_entities = MagicMock()

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [
            DummyEntity(f"{DOMAIN}_1_light", device_id=1),
            DummyEntity(f"{DOMAIN}_2_cover", device_id=2),
        ],
        logger=MagicMock(),
        platform_name="light",
    )

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_1_light"
    ]


def test_dynamic_entities_filter_uses_source_device_id(monkeypatch) -> None:
    """event 等实体使用 _source_device_id 时仍应被设备过滤识别."""
    coordinator = coordinator_with_device_filter(
        {"enabled": True, "exclude": {"devices": ["2"]}}
    )
    coordinator.hass = hass_with_state(None)
    patch_entity_registry(monkeypatch, [])
    entry = entry_with_unload_hook()
    add_entities = MagicMock()

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [
            DummyEntity(f"{DOMAIN}_1_button_event", source_device_id=1),
            DummyEntity(f"{DOMAIN}_2_button_event", source_device_id=2),
        ],
        logger=MagicMock(),
        platform_name="event",
    )

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_1_button_event"
    ]


def test_dynamic_entities_filter_uses_unique_id_fallback(monkeypatch) -> None:
    """缺少显式 device id 属性时，可严格从 unique_id 解析数字设备 id."""
    coordinator = coordinator_with_device_filter(
        {"enabled": True, "exclude": {"devices": ["2"]}}
    )
    coordinator.hass = hass_with_state(None)
    patch_entity_registry(monkeypatch, [])
    entry = entry_with_unload_hook()
    add_entities = MagicMock()

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [
            DummyEntity(f"{DOMAIN}_1_light"),
            DummyEntity(f"{DOMAIN}_2_light"),
        ],
        logger=MagicMock(),
        platform_name="light",
    )

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_1_light"
    ]


def test_dynamic_entities_filter_is_disabled_without_registry_context() -> None:
    """无法判断新旧实体时保持旧行为，避免误伤既有实体恢复."""
    coordinator = coordinator_with_device_filter(
        {"enabled": True, "exclude": {"devices": ["2"]}}
    )
    entry = entry_with_unload_hook()
    add_entities = MagicMock()

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [
            DummyEntity(f"{DOMAIN}_1_light", device_id=1),
            DummyEntity(f"{DOMAIN}_2_light", device_id=2),
        ],
        logger=MagicMock(),
        platform_name="light",
    )

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_1_light",
        "yeelight_pro_2_light",
    ]


def test_dynamic_entities_filter_preserves_non_device_entities_with_registry(
    monkeypatch,
) -> None:
    """有 registry context 时仍应保留 scene/group/house 等辅助实体."""
    coordinator = coordinator_with_device_filter(
        {"enabled": True, "include": {"categories": ["light"]}}
    )
    coordinator.hass = hass_with_state(None)
    entry = entry_with_unload_hook()
    add_entities = MagicMock()
    patch_entity_registry(monkeypatch, [])

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_scene_1")],
        logger=MagicMock(),
        platform_name="scene",
    )

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_scene_1"
    ]


def test_dynamic_entities_filter_does_not_restore_user_disabled_entry(
    monkeypatch,
) -> None:
    """过滤逻辑不得绕过用户禁用 registry entry 的既有保护."""
    coordinator = coordinator_with_device_filter(
        {"enabled": True, "include": {"categories": ["light"]}}
    )
    coordinator.hass = hass_with_state(None)
    entry = entry_with_unload_hook()
    add_entities = MagicMock()
    patch_entity_registry(
        monkeypatch,
        [
            registry_entry(
                unique_id=f"{DOMAIN}_1_light",
                entity_id="light.one",
                domain="light",
                disabled_by="user",
            )
        ],
    )

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_1_light", device_id=1)],
        logger=MagicMock(),
        platform_name="light",
    )

    add_entities.assert_not_called()


def test_dynamic_entities_filter_allows_existing_registry_restore(monkeypatch) -> None:
    """过滤只阻止全新实体，不能阻断已注册实体恢复运行态."""
    coordinator = coordinator_with_device_filter(
        {"enabled": True, "exclude": {"devices": ["1"]}}
    )
    coordinator.hass = hass_with_state(None)
    entry = entry_with_unload_hook()
    add_entities = MagicMock()
    patch_entity_registry(
        monkeypatch,
        [
            registry_entry(
                unique_id=f"{DOMAIN}_1_light",
                entity_id="light.one",
                domain="light",
            )
        ],
    )

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_1_light", device_id=1)],
        logger=MagicMock(),
        platform_name="light",
    )

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_1_light"
    ]
