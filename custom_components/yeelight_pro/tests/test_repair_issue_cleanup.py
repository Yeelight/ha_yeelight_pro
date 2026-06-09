"""Tests for Yeelight Pro Repairs issue cleanup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.repair_issues import (
    TOPOLOGY_CHANGED_ISSUE,
    async_create_topology_changed_issue,
    async_delete_topology_changed_issues,
)


def test_create_topology_changed_issue_deletes_stale_entry_issues(
    hass: HomeAssistant,
) -> None:
    """拓扑代数跳变时应清理同一 config entry 下残留的旧 Repairs issue."""
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
        automations=[],
    )
    current_issue_id = TOPOLOGY_CHANGED_ISSUE.format(
        entry_id="entry-1",
        generation=5,
    )
    issue_registry = SimpleNamespace(
        issues={
            (
                DOMAIN,
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=2),
            ): object(),
            (
                DOMAIN,
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=3),
            ): object(),
            (
                DOMAIN,
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=4),
            ): object(),
            (
                DOMAIN,
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=23),
            ): object(),
            (DOMAIN, current_issue_id): object(),
            (
                DOMAIN,
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-2", generation=3),
            ): object(),
            (DOMAIN, "device_topology_changed_entry-1_latest"): object(),
            (
                "other_domain",
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=1),
            ): object(),
        }
    )

    with patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_get",
        return_value=issue_registry,
    ), patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_create_issue"
    ) as create_issue, patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_delete_issue"
    ) as delete_issue:
        async_create_topology_changed_issue(
            hass,
            entry,
            coordinator,
            previous_generation=2,
        )

    deleted_issue_ids = {call.args[2] for call in delete_issue.call_args_list}
    assert deleted_issue_ids == {
        TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=2),
        TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=3),
        TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=4),
        TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=23),
    }
    create_issue.assert_called_once()
    assert create_issue.call_args.args[2] == current_issue_id


def test_delete_topology_changed_issues_only_deletes_entry_topology_issues(
    hass: HomeAssistant,
) -> None:
    """关闭 Repairs 开关时只清理本 entry 的拓扑提示."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-1"
    issue_registry = SimpleNamespace(
        issues={
            (
                DOMAIN,
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=1),
            ): object(),
            (
                DOMAIN,
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=7),
            ): object(),
            (
                DOMAIN,
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-2", generation=1),
            ): object(),
            (DOMAIN, "device_topology_changed_entry-1_latest"): object(),
            (
                "other_domain",
                TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=1),
            ): object(),
        }
    )

    with patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_get",
        return_value=issue_registry,
    ), patch(
        "custom_components.yeelight_pro.repair_issues.ir.async_delete_issue"
    ) as delete_issue:
        async_delete_topology_changed_issues(hass, entry)

    deleted_issue_ids = {call.args[2] for call in delete_issue.call_args_list}
    assert deleted_issue_ids == {
        TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=1),
        TOPOLOGY_CHANGED_ISSUE.format(entry_id="entry-1", generation=7),
    }
