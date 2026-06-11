"""Tests for Yeelight Pro Repairs issues."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.repair_issues import (
    TOPOLOGY_CHANGED_ISSUE,
    async_create_topology_changed_issue,
)
from custom_components.yeelight_pro.core.topology_diff import TopologyDiffSummary

HASHED_ENTRY_SCOPE = "5e2d5d1e58e94d76"


def test_create_topology_changed_issue_uses_aggregate_counts(
    hass: HomeAssistant,
) -> None:
    """Repairs issue must use a stable id and non-sensitive aggregate counts."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-1"
    coordinator = SimpleNamespace(
        topology_generation=4,
        devices={1: {"device_id": "secret-device"}},
        gateways={2: {"device_id": "secret-gateway"}},
        areas=[{"id": "area-secret", "name": "Floor 1"}],
        rooms=[{"id": "room-secret"}],
        groups=[{"id": "group-secret"}],
        scenes=[{"id": "scene-secret"}],
        topology_diff_summary=TopologyDiffSummary(
            previous_generation=3,
            current_generation=4,
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
                "gateways": 1,
                "areas": 0,
                "rooms": 0,
                "groups": 0,
                "scenes": 0,
            },
        ),
    )

    with patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_create_issue"
    ) as create_issue, patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_delete_issue"
    ) as delete_issue:
        async_create_topology_changed_issue(
            hass,
            entry,
            coordinator,
            previous_generation=3,
        )

    deleted_issue_ids = {call.args[2] for call in delete_issue.call_args_list}
    assert deleted_issue_ids == {
        TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=3),
        TOPOLOGY_CHANGED_ISSUE.format(entry_id=HASHED_ENTRY_SCOPE, generation=3),
    }
    create_issue.assert_called_once_with(
        hass,
        DOMAIN,
        TOPOLOGY_CHANGED_ISSUE.format(entry_id=HASHED_ENTRY_SCOPE, generation=4),
        data={
            "previous_generation": 3,
            "current_generation": 4,
            "diff_summary": {
                "previous_generation": 3,
                "current_generation": 4,
                "added": {
                    "devices": 1,
                    "gateways": 0,
                    "areas": 1,
                    "rooms": 0,
                    "groups": 0,
                    "scenes": 0,
                },
                "removed": {
                    "devices": 0,
                    "gateways": 0,
                    "areas": 0,
                    "rooms": 0,
                    "groups": 0,
                    "scenes": 0,
                },
                "metadata_changed": {
                    "devices": 0,
                    "gateways": 1,
                    "areas": 0,
                    "rooms": 0,
                    "groups": 0,
                    "scenes": 0,
                },
                "total_added": 2,
                "total_removed": 0,
                "total_metadata_changed": 1,
                "total_changes": 3,
            },
            "devices": 1,
            "gateways": 1,
            "areas": 1,
            "rooms": 1,
            "groups": 1,
            "scenes": 1,
        },
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="device_topology_changed",
        translation_placeholders={
            "devices": "1",
            "gateways": "1",
            "areas": "1",
            "rooms": "1",
            "groups": "1",
            "scenes": "1",
            "added": "2",
            "removed": "0",
            "metadata_changed": "1",
        },
    )
    issue_data = create_issue.call_args.kwargs["data"]
    serialized = json.dumps(issue_data, ensure_ascii=False)
    assert "entry-1" not in create_issue.call_args.args[2]
    assert "secret-device" not in serialized
    assert "secret-gateway" not in serialized
    assert "area-secret" not in serialized
    assert "Floor 1" not in serialized
    assert "room-secret" not in serialized


def test_create_topology_changed_issue_falls_back_to_empty_diff(
    hass: HomeAssistant,
) -> None:
    """旧测试替身没有 diff 属性时也应保持 Repairs issue 兼容."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-1"
    coordinator = SimpleNamespace(
        topology_generation=5,
        devices={},
        gateways={},
        areas=[],
        rooms=[],
        groups=[],
        scenes=[],
    )

    with patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_create_issue"
    ) as create_issue, patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_delete_issue"
    ):
        async_create_topology_changed_issue(
            hass,
            entry,
            coordinator,
            previous_generation=4,
        )

    issue_data = create_issue.call_args.kwargs["data"]
    assert issue_data["diff_summary"]["previous_generation"] == 4
    assert issue_data["diff_summary"]["current_generation"] == 5
    assert issue_data["diff_summary"]["total_changes"] == 0


def test_create_topology_changed_issue_whitelists_diff_summary_fields(
    hass: HomeAssistant,
) -> None:
    """恶意 diff summary 不能把 raw IDs/URL/payload 写入 Repairs issue."""

    class UnsafeTopologySummary:
        def as_dict(self) -> dict:
            return {
                "previous_generation": 1,
                "current_generation": 2,
                "added": {
                    "devices": 1,
                    "device-67890": 1,
                    "raw_device_ids": ["device-secret-1"],
                    "url": "https://api.yeelight.com/apis/iot",
                },
                "removed": {"rooms": 0},
                "metadata_changed": {"groups": 1},
                "total_added": 1,
                "total_removed": 0,
                "total_metadata_changed": 1,
                "total_changes": 2,
                "payload": {"token": "secret-token"},
                "body": "house 12345 device 67890",
            }

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-1"
    coordinator = SimpleNamespace(
        topology_generation=2,
        devices={},
        gateways={},
        areas=[],
        rooms=[],
        groups=[],
        scenes=[],
        topology_diff_summary=UnsafeTopologySummary(),
    )

    with patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_create_issue"
    ) as create_issue, patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_delete_issue"
    ):
        async_create_topology_changed_issue(
            hass,
            entry,
            coordinator,
            previous_generation=1,
        )

    summary = create_issue.call_args.kwargs["data"]["diff_summary"]
    assert summary == {
        "previous_generation": 1,
        "current_generation": 2,
        "total_added": 1,
        "total_removed": 0,
        "total_metadata_changed": 1,
        "total_changes": 2,
        "added": {"devices": 1},
        "removed": {"rooms": 0},
        "metadata_changed": {"groups": 1},
    }
    serialized = json.dumps(create_issue.call_args.kwargs["data"], ensure_ascii=False)
    assert "device-secret-1" not in serialized
    assert "secret-token" not in serialized
    assert "api.yeelight.com" not in serialized
    assert "12345" not in serialized
    assert "67890" not in serialized
