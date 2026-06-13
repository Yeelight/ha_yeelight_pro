"""Diagnostics runtime fixture helpers for Yeelight Pro tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.yeelight_pro.entity_lifecycle import (
    EntityRegistryCleanupAudit,
    EntityRegistryReconcileSummary,
)
from custom_components.yeelight_pro.core.topology_diff import TopologyDiffSummary


def build_aggregate_runtime_coordinator(
    empty_coordinator_factory,
) -> MagicMock:
    """构建 diagnostics 聚合 runtime coordinator double."""
    coordinator = empty_coordinator_factory(
        topology_generation=3,
        topology_diff_summary=TopologyDiffSummary(
            previous_generation=2,
            current_generation=3,
            added={
                "devices": 1,
                "gateways": 0,
                "areas": 1,
                "rooms": 0,
                "groups": 0,
                "scenes": 0,
            },
            removed={
                "devices": 0,
                "gateways": 0,
                "areas": 0,
                "rooms": 0,
                "groups": 0,
                "scenes": 0,
            },
            metadata_changed={
                "devices": 0,
                "gateways": 0,
                "areas": 0,
                "rooms": 1,
                "groups": 0,
                "scenes": 0,
            },
        ),
        product_schema_cache_size=2,
    )
    coordinator.house_id = 429392
    coordinator.analytics_enabled = False
    coordinator.devices = {
        1001: {
            "id": 1001,
            "device_id": "device-secret-1",
            "name": "Kitchen Lamp",
            "category": "light",
            "type": "light",
            "online": True,
            "mac": "AA:BB:CC:DD:EE:FF",
            "product_schema": {
                "components": [
                    {
                        "type": 1,
                        "name": "basic",
                        "properties": [{"propId": "name", "operators": ["set"]}],
                    },
                    {
                        "type": 0,
                        "category": "light",
                        "properties": [
                            {"propId": "p", "format": "bool", "operators": ["set"]},
                            {"propId": "luminance", "access": 4},
                        ],
                    },
                ],
            },
            "ha_product_model": {
                "product": {"model_id": "YL-101"},
                "components": [
                    {
                        "component_id": "component-secret-light",
                        "properties": [
                            {"prop_id": "secret-power", "access": "read_write"},
                            {"prop_id": "secret-level", "access": "read_only"},
                            {"prop_id": "secret-write-only", "access": "write_only"},
                        ],
                        "events": [
                            {
                                "event_id": 99,
                                "name": "secret_event_name",
                                "params": [{"prop_id": "secret-event-param"}],
                            }
                        ],
                        "actions": [
                            {
                                "action_name": "secret_component_action",
                                "params": [{"prop_id": "secret-action-param"}],
                            }
                        ],
                    },
                    {
                        "component_id": "component-secret-sensor",
                        "properties": [],
                        "events": [],
                        "actions": [],
                    },
                ],
                "device_actions": [
                    {
                        "action_name": "secret_device_action",
                        "params": [{"prop_id": "secret-device-action-param"}],
                    }
                ],
            },
            "ha_device_instance": {"device_info": {"identifiers": []}},
        },
        1002: {
            "id": 1002,
            "device_id": "device-secret-2",
            "name": "Door Sensor",
            "category": "contact_sensor",
            "type": "binary_sensor",
            "online": "0",
            "params": {"vendor_private": 7},
            "ha_product_model": {
                "product": {"model_id": "YL-101"},
                "components": [],
                "deviceActions": [],
            },
        },
    }
    coordinator.gateways = {
        2001: {
            "id": 2001,
            "device_id": "gateway-secret",
            "category": "gateway",
            "online": "maybe",
        }
    }
    coordinator.rooms = [{"id": "room-secret", "name": "Kitchen"}]
    coordinator.areas = [{"id": "area-secret", "name": "Floor 1"}]
    coordinator.groups = [{"id": "group-secret"}]
    coordinator.scenes = [{"id": "scene-secret"}]
    coordinator._yeelight_pro_last_entity_registry_reconcile_summary = (
        EntityRegistryReconcileSummary(
            active=150,
            registry_entries=150,
            stale=0,
            pending_stale=0,
            disabled=0,
        )
    )
    coordinator._yeelight_pro_last_entity_registry_cleanup_audit = (
        EntityRegistryCleanupAudit(
            audit_id="audit-safe-1",
            status="dry_run",
            stale_entities=2,
            stale_devices=1,
            disabled_entities=0,
            skipped_entities=0,
            entity_domains={"light": 1, "sensor": 1},
        )
    )
    return coordinator


def aggregate_runtime_secret_markers() -> tuple[str, ...]:
    """返回 diagnostics 输出中绝不能出现的敏感 marker."""
    return (
        "token-secret",
        "429392",
        "https://private-api.example.test/apis/iot",
        "device-secret-1",
        "device-secret-2",
        "gateway-secret",
        "AA:BB:CC:DD:EE:FF",
        "yeelight_pro_device-secret-1_light",
        "yeelight_pro_scene_scene-secret",
        "area-secret",
        "Floor 1",
        "room-secret",
        "group-secret",
        "scene-secret",
        "api.yeelight.com/apis/iot/house/429392",
        "duplicate category",
        "references unknown",
        "component-secret-light",
        "component-secret-sensor",
        "secret-power",
        "secret-level",
        "secret-write-only",
        "secret_event_name",
        "secret-event-param",
        "secret_component_action",
        "secret-action-param",
        "secret_device_action",
        "secret-device-action-param",
        "YL-101",
        "house-secret",
    )
