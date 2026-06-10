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

HASHED_ENTRY_SCOPE = "5e2d5d1e58e94d76"
OTHER_HASHED_ENTRY_SCOPE = "edda7b47233f9790"


def _issue_id(entry_scope: str, generation: int | str) -> str:
    """构造测试用拓扑 Repairs issue id."""
    return TOPOLOGY_CHANGED_ISSUE.format(
        entry_id=entry_scope,
        generation=generation,
    )


def test_create_topology_changed_issue_deletes_stale_entry_issues(
    hass: HomeAssistant,
) -> None:
    """拓扑代数跳变时应清理同一 entry 的新旧 Repairs issue."""
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
    current_issue_id = _issue_id(HASHED_ENTRY_SCOPE, 5)
    issue_registry = SimpleNamespace(
        issues={
            (DOMAIN, _issue_id("entry-1", 2)): object(),
            (DOMAIN, _issue_id("entry-1", 3)): object(),
            (DOMAIN, _issue_id("entry-1", 4)): object(),
            (DOMAIN, _issue_id("entry-1", 23)): object(),
            (DOMAIN, _issue_id(HASHED_ENTRY_SCOPE, 2)): object(),
            (DOMAIN, _issue_id(HASHED_ENTRY_SCOPE, 3)): object(),
            (DOMAIN, _issue_id(HASHED_ENTRY_SCOPE, 4)): object(),
            (DOMAIN, _issue_id(HASHED_ENTRY_SCOPE, 23)): object(),
            (DOMAIN, current_issue_id): object(),
            (DOMAIN, _issue_id("entry-2", 3)): object(),
            (DOMAIN, _issue_id(OTHER_HASHED_ENTRY_SCOPE, 3)): object(),
            (DOMAIN, _issue_id("entry-1", "latest")): object(),
            (DOMAIN, _issue_id(HASHED_ENTRY_SCOPE, "latest")): object(),
            ("other_domain", _issue_id("entry-1", 1)): object(),
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
        _issue_id("entry-1", 2),
        _issue_id("entry-1", 3),
        _issue_id("entry-1", 4),
        _issue_id("entry-1", 23),
        _issue_id(HASHED_ENTRY_SCOPE, 2),
        _issue_id(HASHED_ENTRY_SCOPE, 3),
        _issue_id(HASHED_ENTRY_SCOPE, 4),
        _issue_id(HASHED_ENTRY_SCOPE, 23),
    }
    create_issue.assert_called_once()
    assert create_issue.call_args.args[2] == current_issue_id
    assert "entry-1" not in create_issue.call_args.args[2]


def test_delete_topology_changed_issues_only_deletes_entry_topology_issues(
    hass: HomeAssistant,
) -> None:
    """关闭 Repairs 开关时只清理本 entry 的新旧拓扑提示."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-1"
    issue_registry = SimpleNamespace(
        issues={
            (DOMAIN, _issue_id("entry-1", 1)): object(),
            (DOMAIN, _issue_id("entry-1", 7)): object(),
            (DOMAIN, _issue_id(HASHED_ENTRY_SCOPE, 1)): object(),
            (DOMAIN, _issue_id(HASHED_ENTRY_SCOPE, 7)): object(),
            (DOMAIN, _issue_id("entry-2", 1)): object(),
            (DOMAIN, _issue_id(OTHER_HASHED_ENTRY_SCOPE, 1)): object(),
            (DOMAIN, _issue_id("entry-1", "latest")): object(),
            (DOMAIN, _issue_id(HASHED_ENTRY_SCOPE, "latest")): object(),
            ("other_domain", _issue_id("entry-1", 1)): object(),
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
        _issue_id("entry-1", 1),
        _issue_id("entry-1", 7),
        _issue_id(HASHED_ENTRY_SCOPE, 1),
        _issue_id(HASHED_ENTRY_SCOPE, 7),
    }
