"""Tests for dynamic entity discovery after coordinator refresh."""
from __future__ import annotations

from collections.abc import Iterable
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

from homeassistant.helpers.entity import Entity

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.dynamic_entities import async_track_dynamic_entities

from .dynamic_entity_helpers import (
    DummyEntity,
    entry_with_unload_hook,
    hass_with_state,
    patch_entity_registry,
    registry_entry,
)


def test_dynamic_entities_adds_only_new_unique_ids() -> None:
    """重复 listener 调用只应补加未见过的 unique_id."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.items = ["one"]
    entry = entry_with_unload_hook()
    listeners: list = []

    def _add_listener(listener):
        listeners.append(listener)
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)
    add_entities = MagicMock()

    def _entities_for_items(current) -> Iterable[Entity]:
        """按测试替身上的 items 生成实体."""
        return [DummyEntity(f"{DOMAIN}_{item}") for item in current.items]

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        _entities_for_items,
        logger=MagicMock(),
        platform_name="dummy",
    )

    assert add_entities.call_count == 1
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_one"
    ]
    assert len(listeners) == 1
    entry.async_on_unload.assert_called_once()

    listeners[0]()
    assert add_entities.call_count == 1

    coordinator.items.append("two")
    listeners[0]()

    assert add_entities.call_count == 2
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_two"
    ]


def test_dynamic_entities_rescans_when_generation_is_unchanged() -> None:
    """投影规则/Schema 恢复新增候选时，同一拓扑代数也应补建实体."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.items = ["one"]
    coordinator.topology_generation = 7
    entry = entry_with_unload_hook()
    listeners: list = []

    def _add_listener(listener):
        listeners.append(listener)
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)
    add_entities = MagicMock()

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
        logger=MagicMock(),
        platform_name="dummy",
    )

    assert add_entities.call_count == 1

    coordinator.items.append("two")
    listeners[0]()

    assert coordinator.topology_generation == 7
    assert add_entities.call_count == 2
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_two"
    ]


def test_dynamic_entity_scan_logs_aggregate_counts(caplog) -> None:
    """动态实体扫描日志应只输出聚合计数，不泄露 unique_id."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.items = ["one", "one", "two"]
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    entry = entry_with_unload_hook()
    add_entities = MagicMock()
    logger = logging.getLogger("custom_components.yeelight_pro.tests.dynamic_scan")

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        async_track_dynamic_entities(
            entry,
            coordinator,
            add_entities,
            lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
            logger=logger,
            platform_name="dummy",
        )

    assert "Dynamic Yeelight Pro entity scan: platform=dummy" in caplog.text
    assert "candidates=3" in caplog.text
    assert "added=2" in caplog.text
    assert "duplicate_batch_unique_id" in caplog.text
    assert "yeelight_pro_one" not in caplog.text
    assert "yeelight_pro_two" not in caplog.text


def test_dynamic_entities_readds_when_registry_entry_was_removed(monkeypatch) -> None:
    """registry entry 已不存在时，同一 unique_id 恢复应允许重新 add。"""
    coordinator = MagicMock()
    coordinator.hass = hass_with_state(None)
    coordinator.items = ["one"]
    entry = entry_with_unload_hook()
    listeners: list = []

    def _add_listener(listener):
        listeners.append(listener)
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)
    add_entities = MagicMock()
    patch_entity_registry(monkeypatch, [])

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
        logger=MagicMock(),
        platform_name="light",
    )
    listeners[0]()

    assert add_entities.call_count == 2
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_one"
    ]


def test_dynamic_entities_skips_user_disabled_registry_entry(monkeypatch) -> None:
    """用户禁用的 registry entry 不应被动态 helper 反复 add。"""
    coordinator = MagicMock()
    coordinator.hass = hass_with_state(None)
    coordinator.items = ["one"]
    entry = entry_with_unload_hook()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    add_entities = MagicMock()
    patch_entity_registry(
        monkeypatch,
        [
            registry_entry(
                unique_id="yeelight_pro_one",
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
        lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
        logger=MagicMock(),
        platform_name="light",
    )

    add_entities.assert_not_called()


def test_dynamic_entities_restores_integration_disabled_registry_entry(
    monkeypatch,
) -> None:
    """集成自动禁用的 registry entry 当前又有候选时，应解除禁用并恢复运行态。"""
    coordinator = MagicMock()
    coordinator.hass = hass_with_state(None)
    coordinator.items = ["one"]
    entry = entry_with_unload_hook()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    add_entities = MagicMock()
    registry = MagicMock()
    entries = [
        registry_entry(
            unique_id="yeelight_pro_one",
            entity_id="light.one",
            domain="light",
            disabled_by="integration",
        )
    ]
    monkeypatch.setattr(
        "custom_components.yeelight_pro.dynamic_entities.er.async_get",
        lambda hass: registry,
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.dynamic_entities.er."
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: entries,
    )

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
        logger=MagicMock(),
        platform_name="light",
    )

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_one"
    ]
    registry.async_update_entity.assert_called_once_with(
        "light.one",
        disabled_by=None,
    )


def test_dynamic_entities_readds_registered_entity_missing_runtime_state(monkeypatch) -> None:
    """已注册但当前 runtime state 缺失时，应允许提交实体恢复运行态。"""
    coordinator = MagicMock()
    coordinator.hass = hass_with_state(None)
    coordinator.items = ["one"]
    entry = entry_with_unload_hook()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    add_entities = MagicMock()
    patch_entity_registry(
        monkeypatch,
        [
            registry_entry(
                unique_id="yeelight_pro_one",
                entity_id="light.one",
                domain="light",
            )
        ],
    )

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
        logger=MagicMock(),
        platform_name="light",
    )

    assert add_entities.call_count == 1
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_one"
    ]


def test_dynamic_entities_skips_registered_entity_with_runtime_state(monkeypatch) -> None:
    """已注册且运行态存在的实体不应在拓扑刷新时重复 add。"""
    coordinator = MagicMock()
    coordinator.hass = hass_with_state(SimpleNamespace(state="on"))
    coordinator.items = ["one"]
    entry = entry_with_unload_hook()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    add_entities = MagicMock()
    patch_entity_registry(
        monkeypatch,
        [
            registry_entry(
                unique_id="yeelight_pro_one",
                entity_id="light.one",
                domain="light",
            )
        ],
    )

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
        logger=MagicMock(),
        platform_name="light",
    )

    add_entities.assert_not_called()


def test_dynamic_entities_skips_unique_id_owned_by_another_entry(monkeypatch) -> None:
    """云端/LAN 多 entry 不能重复提交同一个 HA unique_id。"""
    coordinator = MagicMock()
    coordinator.hass = hass_with_state(None)
    coordinator.items = ["one"]
    entry = entry_with_unload_hook()
    entry.entry_id = "lan_entry"
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    add_entities = MagicMock()
    patch_entity_registry(
        monkeypatch,
        [],
        global_entries=[
            registry_entry(
                unique_id="yeelight_pro_one",
                entity_id="light.one",
                domain="light",
                config_entry_id="cloud_entry",
            )
        ],
    )

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
        logger=MagicMock(),
        platform_name="light",
    )

    add_entities.assert_not_called()


def test_dynamic_entities_readds_registered_entity_with_restored_state(
    monkeypatch,
) -> None:
    """HA 仅从 registry 恢复的 state 不能阻止平台重新提供实体。"""
    coordinator = MagicMock()
    coordinator.hass = hass_with_state(
        SimpleNamespace(
            state="unavailable",
            attributes={"restored": True},
        )
    )
    coordinator.items = ["one"]
    entry = entry_with_unload_hook()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    add_entities = MagicMock()
    patch_entity_registry(
        monkeypatch,
        [
            registry_entry(
                unique_id="yeelight_pro_one",
                entity_id="light.one",
                domain="light",
            )
        ],
    )

    async_track_dynamic_entities(
        entry,
        coordinator,
        add_entities,
        lambda current: [DummyEntity(f"{DOMAIN}_{item}") for item in current.items],
        logger=MagicMock(),
        platform_name="light",
    )

    assert add_entities.call_count == 1
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_one"
    ]
