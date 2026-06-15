"""Multi-component curtain projection regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.projector.cover import project_covers

from .projection_helpers import projection_payload


def multi_curtain_payload() -> dict:
    """Build a schema-aware payload with two independent curtain components."""
    payload = projection_payload(
        device_id="curtain-dual-1",
        category="curtain",
        component_id="curtain_1",
        state={"cp": 10, "tp": 30},
        component_category="curtain",
    )
    payload["params"] = {
        "1-cp": 10,
        "1-tp": 30,
        "1-cra": 45,
        "1-tra": 90,
        "2-cp": 90,
        "2-tp": 40,
        "2-cra": 135,
        "2-tra": 180,
    }
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "curtain_1": {
                "cp": "1-cp",
                "tp": "1-tp",
                "cra": "1-cra",
                "tra": "1-tra",
            },
            "curtain_2": {
                "cp": "2-cp",
                "tp": "2-tp",
                "cra": "2-cra",
                "tra": "2-tra",
            },
        }
    }
    payload["ha_device_instance"]["components"] = [
        {
            "component_id": "curtain_1",
            "category": "zebra blinds",
            "available": True,
            "state": {"cp": 10, "tp": 30, "cra": 45, "tra": 90},
        },
        {
            "component_id": "curtain_2",
            "category": "zebra blinds",
            "available": True,
            "state": {"cp": 90, "tp": 40, "cra": 135, "tra": 180},
        },
    ]
    payload["ha_product_model"]["components"] = [
        _curtain_schema_component("curtain_1"),
        _curtain_schema_component("curtain_2"),
    ]
    return payload


def test_multi_curtain_components_create_cover_candidates() -> None:
    """候选层必须保留每个窗帘组件，供 registry cleanup 正确对账."""
    candidates = [
        item
        for item in iter_device_entity_candidates(multi_curtain_payload())
        if item.platform == "cover"
    ]

    assert [(item.component_id, item.unique_id) for item in candidates] == [
        ("curtain_1", "yeelight_pro_curtain-dual-1_curtain_1"),
        ("curtain_2", "yeelight_pro_curtain-dual-1_curtain_2"),
    ]
    assert [item.source for item in candidates] == ["device", "device"]
    assert all(item.device_id == "curtain-dual-1" for item in candidates)


def test_multi_curtain_projection_reads_component_scoped_state_keys() -> None:
    """组件 state 稀疏时 cover 位置仍应读取 N-cp/N-tp 原始键."""
    payload = multi_curtain_payload()
    for component in payload["ha_device_instance"]["components"]:
        component["state"] = {}

    projections = project_covers(payload, domain="yeelight_pro")

    assert [(item.component_id, item.current_cover_position) for item in projections] == [
        ("curtain_1", 10),
        ("curtain_2", 90),
    ]
    assert [item.target_cover_position for item in projections] == [30, 40]
    assert [item.target_position_key for item in projections] == ["1-tp", "2-tp"]
    assert [item.current_cover_tilt_position for item in projections] == [25, 75]
    assert [item.target_cover_tilt_position for item in projections] == [50, 100]
    assert [item.target_tilt_position_key for item in projections] == ["1-tra", "2-tra"]


def test_zebra_blind_schema_exposes_tilt_without_current_state() -> None:
    """schema 已声明 tra/cra 时，缺少当前读值也应保留 tilt 控制能力."""
    payload = multi_curtain_payload()
    for component in payload["ha_device_instance"]["components"]:
        component["state"] = {}
    payload["params"] = {
        "1-cp": 10,
        "1-tp": 30,
        "2-cp": 90,
        "2-tp": 40,
    }

    projections = project_covers(payload, domain="yeelight_pro")

    assert [item.current_cover_tilt_position for item in projections] == [None, None]
    assert [item.target_tilt_position_key for item in projections] == ["1-tra", "2-tra"]


def _curtain_schema_component(component_id: str) -> dict:
    """Return product-schema evidence for one curtain component."""
    return {
        "component_id": component_id,
        "category": "curtain",
        "name": "zebra blinds",
        "component_type": "zebra blinds",
        "properties": [
            {"prop_id": "cp", "access": "read"},
            {"prop_id": "tp", "access": "read_write"},
            {"prop_id": "cra", "access": "read"},
            {"prop_id": "tra", "access": "read_write"},
        ],
        "events": [],
    }

__all__ = ["multi_curtain_payload"]
