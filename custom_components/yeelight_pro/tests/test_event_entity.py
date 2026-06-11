"""Event entity behavior tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.yeelight_pro.event import YeelightProEventEntity


def _event_device(events: list[dict]) -> dict:
    """Build a minimal event device payload."""
    return {
        "id": 228215,
        "device_id": 228215,
        "category": "scene_panel",
        "type": "event",
        "online": True,
        "ha_product_model": {
            "product": {
                "model_id": "scene-panel-model",
                "category": "scene_panel",
                "name": "Scene Panel",
                "manufacturer": "Yeelight",
            },
            "components": [
                {
                    "component_id": "scene_panel",
                    "name": "Scene Panel",
                    "category": "scene_panel",
                    "component_type": "normal",
                    "events": events,
                }
            ],
        },
        "ha_device_instance": {
            "device_id": "228215",
            "name": "Scene Panel",
            "online": True,
            "components": [
                {
                    "component_id": "scene_panel",
                    "category": "scene_panel",
                    "available": True,
                    "state": {},
                }
            ],
        },
    }


def test_event_entity_event_types_follow_latest_projection() -> None:
    """schema 刷新后已有 event 实体应读取最新事件类型."""
    coordinator = MagicMock()
    coordinator.get_device.return_value = _event_device(
        [{"event_id": 1, "name": "click"}]
    )
    entity = YeelightProEventEntity(
        coordinator,
        228215,
        component_id="scene_panel",
    )

    assert entity.event_types == ["click"]

    coordinator.get_device.return_value = _event_device(
        [
            {"event_id": 1, "name": "click"},
            {"event_id": 2, "name": "hold"},
            {"event_id": 10, "name": "knob spin"},
        ]
    )

    assert entity.event_types == ["click", "hold", "knob_spin"]


def test_event_entity_handles_missing_device_payload() -> None:
    """设备拓扑短暂缺失时 event 不能向 projector 传 None."""
    coordinator = MagicMock()
    coordinator.get_device.return_value = None

    entity = YeelightProEventEntity(
        coordinator,
        228215,
        component_id="scene_panel",
    )

    assert entity.available is False
    assert entity.name is None
    assert entity.device_info is None
