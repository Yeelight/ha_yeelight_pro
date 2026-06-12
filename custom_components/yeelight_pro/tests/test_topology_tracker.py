"""TopologyTracker 纯逻辑回归测试."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from custom_components.yeelight_pro.core.topology_diff import TOPOLOGY_COLLECTIONS
from custom_components.yeelight_pro.core.topology_tracker import TopologyTracker


EMPTY_TOPOLOGY: dict[str, Any] = {
    "devices": {},
    "gateways": {},
    "areas": [],
    "rooms": [],
    "groups": [],
    "scenes": [],
    "houses": [],
}


def _device(
    device_id: str,
    *,
    name: str = "Lamp",
    category: str = "light",
    room_id: str = "room-1",
) -> dict[str, Any]:
    """构造只包含拓扑字段的设备 payload."""
    return {
        "id": device_id,
        "device_id": device_id,
        "name": name,
        "category": category,
        "type": category,
        "pid": 100,
        "roomId": room_id,
        "properties": [{"propId": "p", "value": True}],
    }


def _update(
    tracker: TopologyTracker,
    *,
    devices: Mapping[Any, Mapping[str, Any]] | None = None,
    gateways: Mapping[Any, Mapping[str, Any]] | None = None,
    areas: list[dict[str, Any]] | None = None,
    rooms: list[dict[str, Any]] | None = None,
    groups: list[dict[str, Any]] | None = None,
    scenes: list[dict[str, Any]] | None = None,
    houses: list[dict[str, Any]] | None = None,
) -> None:
    """用默认空拓扑降低单测噪音."""
    tracker.update(
        devices=devices or EMPTY_TOPOLOGY["devices"],
        gateways=gateways or EMPTY_TOPOLOGY["gateways"],
        areas=areas or EMPTY_TOPOLOGY["areas"],
        rooms=rooms or EMPTY_TOPOLOGY["rooms"],
        groups=groups or EMPTY_TOPOLOGY["groups"],
        scenes=scenes or EMPTY_TOPOLOGY["scenes"],
        houses=houses or EMPTY_TOPOLOGY["houses"],
    )


def _assert_empty_diff(tracker: TopologyTracker) -> None:
    """断言当前 diff 已清空且所有分类计数为零."""
    summary = tracker.diff_summary

    assert summary.total_changes == 0
    for collection in TOPOLOGY_COLLECTIONS:
        assert summary.added[collection] == 0
        assert summary.removed[collection] == 0
        assert summary.metadata_changed[collection] == 0


def test_initial_generation_and_topology_diff_are_empty() -> None:
    """初始 tracker 不应声明任何拓扑变化."""
    tracker = TopologyTracker()

    assert tracker.generation == 0
    assert tracker.diff_summary.previous_generation == 0
    assert tracker.diff_summary.current_generation == 0
    _assert_empty_diff(tracker)


def test_first_update_establishes_baseline_without_diff() -> None:
    """首次载入设备应建立拓扑基线，但不误报新增变化."""
    tracker = TopologyTracker()

    _update(tracker, devices={"lamp-1": _device("lamp-1")})

    assert tracker.generation == 1
    assert tracker.diff_summary.previous_generation == 0
    assert tracker.diff_summary.current_generation == 1
    _assert_empty_diff(tracker)


def test_repeated_update_with_same_devices_keeps_generation_and_empty_diff() -> None:
    """同一批设备重复 update 不应递增 generation."""
    tracker = TopologyTracker()

    _update(tracker, devices={"lamp-1": _device("lamp-1")})
    first_generation = tracker.generation
    _update(tracker, devices={"lamp-1": _device("lamp-1")})

    assert first_generation == 1
    assert tracker.generation == first_generation
    assert tracker.diff_summary.previous_generation == first_generation
    assert tracker.diff_summary.current_generation == first_generation
    _assert_empty_diff(tracker)


def test_update_ignores_runtime_state_changes() -> None:
    """在线、属性和组件状态变化不应被识别为拓扑变化."""
    tracker = TopologyTracker()
    first_device = {
        **_device("lamp-1"),
        "online": True,
        "params": {"p": True, "l": 20},
        "ha_device_instance": {
            "components": [
                {
                    "component_id": "light_1",
                    "component_type": "light",
                    "category": "light",
                    "available": True,
                    "state": {"p": True, "l": 20},
                }
            ],
        },
    }
    second_device = {
        **_device("lamp-1"),
        "online": False,
        "params": {"p": False, "l": 80},
        "properties": [
            {"propId": "p", "value": False},
            {"propId": "l", "value": 80},
        ],
        "ha_device_instance": {
            "components": [
                {
                    "component_id": "light_1",
                    "component_type": "light",
                    "category": "light",
                    "available": False,
                    "state": {"p": False, "l": 80},
                }
            ],
        },
    }

    _update(tracker, devices={"lamp-1": first_device})
    first_generation = tracker.generation
    _update(tracker, devices={"lamp-1": second_device})

    assert tracker.generation == first_generation
    _assert_empty_diff(tracker)


def test_update_marks_removed_devices() -> None:
    """设备从拓扑中消失时应标记 removed."""
    tracker = TopologyTracker()

    _update(
        tracker,
        devices={
            "lamp-1": _device("lamp-1"),
            "lamp-2": _device("lamp-2"),
        },
    )
    _update(tracker, devices={"lamp-1": _device("lamp-1")})

    assert tracker.generation == 2
    assert tracker.diff_summary.removed["devices"] == 1
    assert tracker.diff_summary.total_removed == 1
    assert tracker.diff_summary.total_added == 0
    assert tracker.diff_summary.total_metadata_changed == 0


@pytest.mark.parametrize(
    ("changed_device", "reason"),
    [
        (_device("lamp-1", name="Renamed Lamp"), "name"),
        (_device("lamp-1", room_id="room-2"), "area"),
        (_device("lamp-1", category="relay_switch"), "category"),
    ],
)
def test_update_marks_device_metadata_changes(
    changed_device: dict[str, Any],
    reason: str,
) -> None:
    """设备名称、区域或品类变化应标记 metadata_changed."""
    tracker = TopologyTracker()

    _update(tracker, devices={"lamp-1": _device("lamp-1")})
    _update(tracker, devices={"lamp-1": changed_device})

    assert reason in {"name", "area", "category"}
    assert tracker.generation == 2
    assert tracker.diff_summary.metadata_changed["devices"] == 1
    assert tracker.diff_summary.total_metadata_changed == 1
    assert tracker.diff_summary.total_added == 0
    assert tracker.diff_summary.total_removed == 0


def test_update_ignores_different_mapping_key_order() -> None:
    """payload key 顺序变化不应误判为拓扑变化."""
    tracker = TopologyTracker()
    first_device = {
        "id": "lamp-1",
        "device_id": "lamp-1",
        "name": "Lamp",
        "type": "light",
        "category": "light",
        "pid": 100,
        "roomId": "room-1",
        "ha_device_instance": {
            "device_info": {
                "identifiers": {"domain": "yeelight_pro", "id": "lamp-1"},
                "via_device": {"domain": "yeelight_pro", "id": "gateway-1"},
            },
            "components": [
                {
                    "component_id": 4,
                    "component_type": "light",
                    "category": "light",
                }
            ],
        },
    }
    second_device = {
        "ha_device_instance": {
            "components": [
                {
                    "category": "light",
                    "component_type": "light",
                    "component_id": 4,
                }
            ],
            "device_info": {
                "via_device": {"id": "gateway-1", "domain": "yeelight_pro"},
                "identifiers": {"id": "lamp-1", "domain": "yeelight_pro"},
            },
        },
        "roomId": "room-1",
        "pid": 100,
        "category": "light",
        "type": "light",
        "name": "Lamp",
        "device_id": "lamp-1",
        "id": "lamp-1",
    }

    _update(tracker, devices={"lamp-1": first_device})
    first_generation = tracker.generation
    _update(tracker, devices={"lamp-1": second_device})

    assert tracker.generation == first_generation
    _assert_empty_diff(tracker)


def test_repeated_unchanged_update_clears_previous_diff() -> None:
    """重复同一拓扑应清空上一轮 diff，不重置 generation."""
    tracker = TopologyTracker()

    _update(tracker, devices={"lamp-1": _device("lamp-1")})
    _update(
        tracker,
        devices={
            "lamp-1": _device("lamp-1"),
            "lamp-2": _device("lamp-2"),
        },
    )
    assert tracker.generation == 2
    assert tracker.diff_summary.total_added == 1

    _update(
        tracker,
        devices={
            "lamp-1": _device("lamp-1"),
            "lamp-2": _device("lamp-2"),
        },
    )

    assert tracker.generation == 2
    assert tracker.diff_summary.previous_generation == 2
    assert tracker.diff_summary.current_generation == 2
    _assert_empty_diff(tracker)
