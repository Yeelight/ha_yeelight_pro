"""Diagnostics release preflight contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_diagnostics_contract_check_requires_all_client_capability_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝缺少完整 client capabilities 断言的诊断测试."""
    component_root = _build_component_root(tmp_path)
    _write_client_capability_diagnostics(component_root)
    _write_diagnostics_contract_tests(component_root, include_lan_control=False)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_diagnostics_redaction_contract_tests()

    assert (
        "tests/test_diagnostics_capabilities.py missing live LAN control capability "
        "is explicit: lan_control"
    ) in errors


def test_diagnostics_contract_check_rejects_enabled_live_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应阻止未验证 disabled live capability 被改成 true."""
    component_root = _build_component_root(tmp_path)
    _write_client_capability_diagnostics(component_root, mqtt_subscription=True)
    _write_diagnostics_contract_tests(component_root)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_diagnostics_redaction_contract_tests()

    assert "diagnostics.py live capability must remain false: mqtt_subscription" in errors


def test_diagnostics_contract_check_rejects_ambiguous_oauth_flow_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝恢复容易误解的 OAuth flow capability key."""
    component_root = _build_component_root(tmp_path)
    _write_client_capability_diagnostics(
        component_root,
        include_ambiguous_oauth=True,
    )
    _write_diagnostics_contract_tests(component_root)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_diagnostics_redaction_contract_tests()

    assert any("oauth_authorization_code_flow" in error for error in errors)


def test_diagnostics_contract_check_rejects_legacy_websocket_skeleton_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝把 WebSocket runtime 退回 skeleton 语义."""
    component_root = _build_component_root(tmp_path)
    _write_client_capability_diagnostics(
        component_root,
        include_legacy_websocket_skeleton=True,
    )
    _write_diagnostics_contract_tests(component_root)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_diagnostics_redaction_contract_tests()

    assert any("websocket_transport_skeleton" in error for error in errors)


def test_diagnostics_contract_check_rejects_sse_subscription_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝增加 SSE capability，事件通知只走 WebSocket."""
    component_root = _build_component_root(tmp_path)
    _write_client_capability_diagnostics(
        component_root,
        include_sse_subscription=True,
    )
    _write_diagnostics_contract_tests(component_root)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_diagnostics_redaction_contract_tests()

    assert any("sse_subscription" in error for error in errors)


def test_diagnostics_contract_check_rejects_eventsource_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝 EventSource/SSE 同义 capability，事件通知只走 WebSocket."""
    component_root = _build_component_root(tmp_path)
    _write_client_capability_diagnostics(
        component_root,
        include_eventsource_subscription=True,
    )
    _write_diagnostics_contract_tests(component_root)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_diagnostics_redaction_contract_tests()

    assert any("eventsource_subscription" in error for error in errors)
    assert any("server_sent_events" in error for error in errors)


def _build_component_root(tmp_path: Path) -> Path:
    """Create a minimal synthetic component tree for preflight checks."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    (component_root / "tests").mkdir(parents=True)
    return component_root


def _write_diagnostics_contract_tests(
    component_root: Path,
    *,
    include_lan_control: bool = True,
) -> None:
    """Write minimal diagnostics tests with capability coverage markers."""
    tests_root = component_root / "tests"
    runtime_tokens = (
        "aggregate_runtime_secret_markers option_status runtime_reload_required "
        "platforms_match_options debug_mode_enabled scan_interval_seconds "
        "spec_runtime_inventory entity_registry_reconcile"
    )
    option_tokens = (
        "option_status_diagnostics "
        "test_option_status_normalizes_legacy_runtime_options "
        "runtime_reload_required platforms_match_options debug_mode_enabled "
        "scan_interval_seconds import_filter_active"
    )
    inventory_tokens = (
        "test_spec_runtime_inventory_uses_spec_correction_access_rules "
        "spec_runtime_inventory_diagnostics readable_properties writable_properties"
    )
    helper_tokens = (
        "build_empty_diagnostics_coordinator build_filter_preview_coordinator "
        "build_aggregate_runtime_coordinator diagnostics_runtime_helpers"
    )
    runtime_helper_tokens = (
        "build_aggregate_runtime_coordinator EntityRegistryReconcileSummary "
        "component-secret-light secret_device_action"
    )
    capability_tokens = (
        "client_capabilities oauth_contract oauth_token_runtime "
        "manual_oauth_authorization_code_exchange oauth_flow "
        "scan_login_contract scan_login_runtime "
        "refresh_token_contract refresh_token_runtime push_message_adapter "
        "runtime_payload_bridge websocket_message_contract push_manager_contract "
        "websocket_transport_runtime lan_discovery_parser lan_message_contract "
        "lan_payload_adapter analytics_contract push_connection "
        "websocket_subscription websocket_event_notifications "
        "local_gateway_control mqtt_subscription analytics_runtime"
    )
    if include_lan_control:
        capability_tokens += " lan_control"

    _write_test_file(
        tests_root / "test_diagnostics_redaction.py",
        (
            "validate_iot_registry topology_diff_summary api.yeelight.com "
            "token-secret device_filter_form_keys room-secret-form"
        ),
    )
    _write_test_file(
        tests_root / "test_diagnostics_filters.py",
        "entity_import_filter_preview relay-secret vacuum-secret",
    )
    _write_test_file(tests_root / "diagnostics_helpers.py", helper_tokens)
    _write_test_file(
        tests_root / "diagnostics_runtime_helpers.py",
        runtime_helper_tokens,
    )
    _write_test_file(tests_root / "test_diagnostics_runtime.py", runtime_tokens)
    _write_test_file(tests_root / "test_diagnostics_inventory.py", inventory_tokens)
    _write_test_file(
        tests_root / "test_diagnostics_capabilities.py",
        capability_tokens,
    )
    _write_test_file(
        tests_root / "test_diagnostic_summaries.py",
        (
            "entity_candidate_diagnostics "
            "entity_import_filter_preview_diagnostics device-secret "
            "preview-automation-secret"
        ),
    )
    _write_test_file(tests_root / "test_diagnostic_options.py", option_tokens)


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")


def _write_client_capability_diagnostics(
    component_root: Path,
    *,
    mqtt_subscription: bool = False,
    include_ambiguous_oauth: bool = False,
    include_legacy_websocket_skeleton: bool = False,
    include_sse_subscription: bool = False,
    include_eventsource_subscription: bool = False,
) -> None:
    """Write a minimal diagnostics module with literal capability flags."""
    ambiguous_oauth = (
        '        "oauth_authorization_code_flow": True,\n'
        if include_ambiguous_oauth
        else ""
    )
    legacy_websocket = (
        '        "websocket_transport_skeleton": True,\n'
        if include_legacy_websocket_skeleton
        else ""
    )
    sse_subscription = (
        '        "sse_subscription": True,\n' if include_sse_subscription else ""
    )
    eventsource_subscription = (
        '        "eventsource_subscription": True,\n'
        '        "server_sent_events": True,\n'
        if include_eventsource_subscription
        else ""
    )
    content = f"""
def _client_capabilities_for_entry(entry):
    return {{
        "oauth_contract": True,
        "oauth_token_runtime": True,
        "manual_oauth_authorization_code_exchange": True,
        "scan_login_contract": True,
        "scan_login_runtime": True,
{ambiguous_oauth.rstrip()}
        "oauth_flow": False,
        "refresh_token_contract": True,
        "refresh_token_runtime": True,
        "push_message_adapter": True,
        "runtime_payload_bridge": True,
        "websocket_message_contract": True,
{legacy_websocket.rstrip()}
        "websocket_transport_runtime": True,
{sse_subscription.rstrip()}
{eventsource_subscription.rstrip()}
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "analytics_contract": True,
        "push_connection": True,
        "websocket_subscription": True,
        "websocket_event_notifications": True,
        "local_gateway_control": True,
        "lan_control": True,
        "mqtt_subscription": {mqtt_subscription},
        "analytics_runtime": True,
    }}
"""
    _write_test_file(component_root / "diagnostics.py", content)
