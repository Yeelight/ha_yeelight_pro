"""Shared helpers for projection matrix tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

DOMAIN = "yeelight_pro"


@dataclass
class LifecycleCoordinator:
    """测试 entity lifecycle 投影收集所需的最小 coordinator 结构."""

    data: Mapping[Any, Mapping[str, Any]]
    scenes: list[dict[str, Any]] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    house_id: int | None = None
    hide_unknown_entities: bool = True


def projection_payload(
    *,
    device_id: str,
    category: str,
    component_id: str,
    state: dict,
    params: dict | None = None,
    product_events: list[dict] | None = None,
    properties: tuple[str, ...] = (),
    product_type: int | None = None,
    online: bool = True,
    component_category: str | None = None,
) -> dict:
    """构造最小 canonical runtime + product payload."""
    component_category = component_category or category
    return {
        "id": device_id,
        "device_id": device_id,
        "name": f"设备 {device_id}",
        "iot_category": category,
        "category": category,
        "type": category,
        "online": online,
        "product_type": product_type,
        "params": dict(params or {}),
        "ha_device_instance": {
            "device_id": device_id,
            "name": f"设备 {device_id}",
            "online": online,
            "device_info": {
                "identifiers": [[DOMAIN, device_id]],
                "manufacturer": "Yeelight",
                "model": category,
                "name": f"设备 {device_id}",
            },
            "components": [
                {
                    "component_id": component_id,
                    "category": component_category,
                    "available": online,
                    "state": dict(state),
                }
            ],
        },
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": f"model-{device_id}",
                "manufacturer": "Yeelight",
                "model": category,
                "category": category,
            },
            "components": [
                {
                    "component_id": component_id,
                    "category": component_category,
                    "name": component_category,
                    "component_type": component_category,
                    "properties": [
                        {
                            "prop_id": prop,
                            "kind": "state",
                            "property_type": "apply",
                            "access": "read_only",
                        }
                        for prop in properties
                    ],
                    "events": list(product_events or []),
                }
            ],
        },
    }
