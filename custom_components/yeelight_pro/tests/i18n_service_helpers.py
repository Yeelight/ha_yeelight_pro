"""Service translation fixtures for local HA i18n verifier tests."""

from __future__ import annotations

from typing import Any


def service_yaml_lines() -> list[str]:
    """Return services.yaml lines used by i18n verifier fixtures."""
    return [
        "assign_areas:",
        "  fields:",
        "    devices:",
        "      selector:",
        "        object:",
        "    area_id:",
        "      selector:",
        "        area:",
        "auto_assign_areas:",
        "  fields:",
        "    gateway_id:",
        "      selector:",
        "        text:",
        "debug_emit_event:",
        "  fields:",
        "    entry_id:",
        "      selector:",
        "        text:",
        "    source_device_id:",
        "      selector:",
        "        text:",
        "    component_id:",
        "      selector:",
        "        text:",
        "    event_type:",
        "      selector:",
        "        text:",
        "    event_attributes:",
        "      selector:",
        "        object:",
        "refresh:",
        "  fields:",
        "    entry_id:",
        "      selector:",
        "        text:",
        "    refresh_product_schemas:",
        "      selector:",
        "        boolean:",
        "cleanup_registry:",
        "  fields:",
        "    entry_id:",
        "      selector:",
        "        text:",
        "    confirm:",
        "      selector:",
        "        boolean:",
        "    audit_id:",
        "      selector:",
        "        text:",
        "refresh_analytics:",
        "  fields:",
        "    entry_id:",
        "      selector:",
        "        text:",
        "    endpoint:",
        "      selector:",
        "        text:",
        "    date_code:",
        "      selector:",
        "        text:",
        "    start_date:",
        "      selector:",
        "        text:",
        "    end_date:",
        "      selector:",
        "        text:",
        "    area_id:",
        "      selector:",
        "        text:",
    ]


def service_translation_payload() -> dict[str, Any]:
    """Return service translations matching the production service boundary."""
    return {
        "assign_areas": {
            "name": "Assign Areas",
            "description": "Assign areas.",
        },
        "auto_assign_areas": {
            "name": "Auto Assign Areas",
            "description": "Auto assign areas.",
        },
        "debug_emit_event": {
            "name": "Emit Debug Event",
            "description": "Emit debug events.",
        },
        "refresh": {
            "name": "Refresh",
            "description": "Refresh Yeelight Pro data.",
            "fields": {
                "refresh_product_schemas": {
                    "name": "Refresh product schemas",
                    "description": "Refetch product schemas.",
                }
            },
        },
        "cleanup_registry": {
            "name": "Registry cleanup",
            "description": "Dry-run and confirm stale entity cleanup.",
            "fields": {
                "entry_id": {
                    "name": "Config entry ID",
                    "description": "Target config entry.",
                },
                "confirm": {
                    "name": "Confirm cleanup",
                    "description": "Confirm the dry-run audit.",
                },
                "audit_id": {
                    "name": "Audit ID",
                    "description": "Audit ID from dry-run.",
                },
            },
        },
        "refresh_analytics": {
            "name": "Refresh Analytics",
            "description": "Refresh aggregate analytics data.",
            "fields": {
                "entry_id": {
                    "name": "Config entry ID",
                    "description": "Target config entry.",
                },
                "endpoint": {
                    "name": "Analytics endpoint",
                    "description": "Endpoint key to refresh.",
                },
                "date_code": {
                    "name": "Date code",
                    "description": "Date code for day, month, or year requests.",
                },
                "start_date": {
                    "name": "Start date",
                    "description": "Trend start date.",
                },
                "end_date": {
                    "name": "End date",
                    "description": "Trend end date.",
                },
                "area_id": {
                    "name": "Area ID",
                    "description": "Optional area ID.",
                },
            },
        },
    }
