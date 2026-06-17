"""Release preflight protocol contract tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_scan_login_contract_check_requires_runtime_coverage_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝空文件冒充扫码登录 runtime 覆盖."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    core_root = component_root / "core"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    core_root.mkdir()
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    _write_test_file(
        component_root / "scan_login_contract.py",
        (
            "CLOUD_REGION_BASE_DOMAINS SCAN_LOGIN_QRCODE_TTL_MS "
            "build_scan_login_qrcode_path build_scan_login_status_path "
            "build_scan_login_qrcode_content parse_scan_login_response cli&"
        ),
    )
    _write_test_file(
        core_root / "scan_login.py",
        "account_base_url create_scan_login_qrcode",
    )
    _write_test_file(
        component_root / "config_flow_scan_login_helpers.py",
        "QrCodeSelector CONF_SCAN_LOGIN_QRCODE cloud_scan_login_schema_for_qrcode",
    )
    _write_test_file(
        component_root / "config_flow_scan_login.py",
        "async_show_progress",
    )
    _write_test_file(
        tests_root / "test_scan_login_contract.py",
        "SCAN_LOGIN_QRCODE_TTL_MS cli&AA:BB:CC:DD:EE:FF&qr-1",
    )
    _write_test_file(tests_root / "test_scan_login_runtime.py", "FakeScanLoginSession")
    _write_test_file(tests_root / "test_config_flow_scan_login_device.py", "")
    _write_test_file(tests_root / "test_config_flow_scan_login.py", "")
    scripts_root = component_root.parent.parent / "scripts"
    scripts_root.mkdir()
    _write_test_file(tests_root / "test_verify_scan_login.py", "")
    _write_test_file(scripts_root / "verify_scan_login.py", "")

    errors = hacs_preflight._check_scan_login_contract_tests()

    assert any("scan-login token model" in error for error in errors)
    assert any("scan-login refresh-token field alias coverage" in error for error in errors)
    assert any("QR countdown expiry derivation helper" in error for error in errors)
    assert any("QR countdown expiry derivation coverage" in error for error in errors)
    assert any("scan-login HA instance device helper" in error for error in errors)
    assert any("HA instance id source for scan-login device" in error for error in errors)
    assert any("scan-login device hash derivation" in error for error in errors)
    assert any("scan-login device prefix boundary" in error for error in errors)
    assert any("scan-login device id privacy coverage" in error for error in errors)
    assert any("scan-login device id uniqueness coverage" in error for error in errors)
    assert any("raw HA instance id leakage regression marker" in error for error in errors)
    assert any("scan-login polling coverage" in error for error in errors)
    assert any("scan-login qrcode creation coverage" in error for error in errors)
    assert any("native Home Assistant QR selector coverage" in error for error in errors)
    assert any("scan-login progress polling coverage" in error for error in errors)
    assert any("scan-login LOGIN token flow coverage" in error for error in errors)
    assert any("production scan-login confirm guard coverage" in error for error in errors)
    assert any("production scan-login device env guard coverage" in error for error in errors)
    assert any("production scan-login bounded-run guard coverage" in error for error in errors)
    assert any("production scan-login redacted summary coverage" in error for error in errors)
    assert any("production scan-login default no-network coverage" in error for error in errors)
    assert any(
        "production scan-login script-path no-network coverage" in error
        for error in errors
    )
    assert any(
        "production scan-login fake-login aggregate coverage" in error
        for error in errors
    )
    assert any("explicit production scan-login confirm flag" in error for error in errors)
    assert any("environment-only scan-login device input" in error for error in errors)
    assert any("diagnostics-safe scan-login probe summary" in error for error in errors)
    assert any(
        "Home Assistant-free scan-login contract path" in error for error in errors
    )
    assert any(
        "Home Assistant-free scan-login contract loader" in error
        for error in errors
    )


def test_push_contract_check_requires_coverage_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝空测试文件冒充 push 契约覆盖."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    core_root = component_root / "core"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    core_root.mkdir()
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    _write_test_file(
        component_root / "push_contract.py",
        "build_push_url build_subscribe_message build_heartbeat_message socket",
    )
    _write_test_file(
        component_root / "push_manager.py",
        "PushTransport PushManager async_handle_push_payload",
    )
    _write_test_file(component_root / "push_transport.py", "ws_connect")
    _write_test_file(component_root / "push_transport_frames.py", "")
    _write_test_file(component_root / "push.py", "")
    _write_test_file(core_root / "runtime_bridge.py", "socket")
    _write_test_file(tests_root / "test_push_contract.py", "")
    _write_test_file(tests_root / "test_push_websocket_contract.py", "")
    _write_test_file(tests_root / "test_push_payloads.py", "")
    _write_test_file(tests_root / "test_push_payload_events.py", "")
    _write_test_file(tests_root / "test_push_manager.py", "FakeTransport")
    _write_test_file(tests_root / "push_transport_helpers.py", "FakeSession")
    _write_test_file(tests_root / "test_push_transport.py", "push_transport_helpers")
    _write_test_file(tests_root / "test_push_transport_reconnect.py", "")
    _write_test_file(
        tests_root / "test_push_transport_failures.py",
        "push_transport_helpers",
    )
    _write_test_file(tests_root / "test_live_runtime.py", "")
    _write_test_file(tests_root / "test_verify_push_websocket.py", "")
    scripts_root = component_root.parent.parent / "scripts"
    scripts_root.mkdir()
    _write_test_file(scripts_root / "verify_push_websocket.py", "")
    _write_test_file(tests_root / "test_runtime_bridge.py", "")
    _write_test_file(tests_root / "test_runtime_bridge_lan_events.py", "")

    errors = hacs_preflight._check_push_contract_tests()

    assert (
        "push_contract.py missing monotonic message id builder: PushMessageBuilder"
    ) in errors
    assert any("WebSocket-only endpoint scheme guard" in error for error in errors)
    assert any(
        "WebSocket-only endpoint rejection coverage" in error for error in errors
    )
    assert any("bounded reconnect policy helper" in error for error in errors)
    assert any("reconnect policy timing coverage" in error for error in errors)
    assert any("reconnect policy pure helper coverage" in error for error in errors)
    assert any("reconnect policy validation coverage" in error for error in errors)
    assert (
        "push_contract.py must remain no-network: socket"
    ) in errors
    assert (
        "push_manager.py missing diagnostics-safe error aggregation: last_error_type"
    ) in errors
    assert any("transport cleanup retry state" in error for error in errors)
    assert any("websocket runtime transport" in error for error in errors)
    assert any("automatic reconnect scheduler" in error for error in errors)
    assert any("automatic reconnect loop" in error for error in errors)
    assert any("recoverable initial-connect error diagnostics" in error for error in errors)
    assert any("session protocol seam" in error for error in errors)
    assert any("subscribe frame send boundary" in error for error in errors)
    assert any("heartbeat frame send boundary" in error for error in errors)
    assert any("documented heartbeat interval use" in error for error in errors)
    assert any("incoming JSON object filter" in error for error in errors)
    assert any("reader failure cleanup boundary" in error for error in errors)
    assert any("start-time payload error coverage" in error for error in errors)
    assert any(
        "recoverable transport start error health coverage" in error
        for error in errors
    )
    assert any("stop failure retry coverage" in error for error in errors)
    assert any("finite websocket stream coverage" in error for error in errors)
    assert any("controllable heartbeat sleep coverage" in error for error in errors)
    assert any("connect subscribe dispatch coverage" in error for error in errors)
    assert any("heartbeat loop cancellation coverage" in error for error in errors)
    assert any("transport stop cleanup coverage" in error for error in errors)
    assert any("transport start idempotency coverage" in error for error in errors)
    assert any("transport reconnect after reader-end coverage" in error for error in errors)
    assert any("transport reconnect retry backoff coverage" in error for error in errors)
    assert any("initial connect failure reconnect coverage" in error for error in errors)
    assert any("subscribe failure cleanup coverage" in error for error in errors)
    assert any("transport stop retry cleanup coverage" in error for error in errors)
    assert any("heartbeat failure cleanup coverage" in error for error in errors)
    assert any("reader failure cleanup coverage" in error for error in errors)
    assert any("callback failure cleanup coverage" in error for error in errors)
    assert any("token validation before connect coverage" in error for error in errors)
    assert any("live WebSocket end-to-end coordinator dispatch coverage" in error for error in errors)
    assert any(
        "WebSocket-only event notification rejects non-WebSocket fallback frames"
        in error
        for error in errors
    )
    assert any("production WebSocket confirm guard coverage" in error for error in errors)
    assert any("production WebSocket token env guard coverage" in error for error in errors)
    assert any("production WebSocket bounded-run guard coverage" in error for error in errors)
    assert any("production WebSocket redacted summary coverage" in error for error in errors)
    assert any("production WebSocket default no-network coverage" in error for error in errors)
    assert any(
        "production WebSocket script-path no-network coverage" in error
        for error in errors
    )
    assert any("explicit production WebSocket confirm flag" in error for error in errors)
    assert any("environment-only push token input" in error for error in errors)
    assert any("diagnostics-safe probe summary" in error for error in errors)
    assert any("Home Assistant-free push contract load path" in error for error in errors)
    assert any("Home Assistant-free pure contract loader" in error for error in errors)
    assert any("field-name-only JSON shape summary" in error for error in errors)
    assert any("shared runtime payload bridge" in error for error in errors)
    assert any("push event privacy filter" in error for error in errors)
    assert any("push prop metadata boundary coverage" in error for error in errors)
    assert any("push event privacy coverage" in error for error in errors)
    assert any("schema event component inference" in error for error in errors)
    assert any("runtime property merge path" in error for error in errors)
    assert any("Bearer prefix regression coverage" in error for error in errors)
    assert any("coordinator bridge coverage" in error for error in errors)
    assert any("start-time payload dispatch coverage" in error for error in errors)
    assert any("LAN coordinator bridge coverage" in error for error in errors)
    assert any("LAN fallback component inference coverage" in error for error in errors)
    assert any("indexed runtime state bridge coverage" in error for error in errors)
    assert any("schema-scaled runtime update rebuild coverage" in error for error in errors)
    assert (
        "core/runtime_bridge.py must remain no-network: socket"
    ) in errors


def test_push_contract_check_rejects_sse_runtime_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """易来事件通知只有 WebSocket，preflight 必须拒绝 SSE runtime 回退。"""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    component_root.mkdir(parents=True)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)
    _write_test_file(
        component_root / "sse_consumer.py",
        (
            'class SSETransport: ...\n'
            '# sse_consumer\n'
            'EventSource("https://example.test/events")\n'
            '"text/event-stream"'
        ),
    )

    errors = hacs_preflight._check_push_contract_tests()

    assert any("SSE runtime path" in error for error in errors)
    assert any("EventSource runtime path" in error for error in errors)
    assert any("SSE content-type runtime path" in error for error in errors)
    assert any("SSE consumer runtime path" in error for error in errors)


def test_lan_contract_check_requires_coverage_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝空测试文件冒充 LAN 契约覆盖."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    core_root = component_root / "core"
    tests_root = component_root / "tests"
    core_root.mkdir(parents=True)
    tests_root.mkdir(parents=True)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    _write_test_file(component_root / "lan_methods.py", "METHOD_POST_PROP socket")
    _write_test_file(
        component_root / "lan_contract.py",
        (
            "LAN_DISCOVERY_MESSAGE LAN_DISCOVERY_PORT LAN_GATEWAY_PORT "
            "parse_discovery_response encode_lan_frame decode_lan_frames"
        ),
    )
    _write_test_file(component_root / "lan_discovery.py", "socket")
    _write_test_file(component_root / "lan_runtime.py", "")
    _write_test_file(component_root / "lan_payload.py", "socket")
    _write_test_file(core_root / "lan_control.py", "async_try_lan_control_device")
    _write_test_file(
        core_root / "coordinator_controls.py",
        "CoordinatorControlMixin async_try_lan_control_device",
    )
    _write_test_file(tests_root / "test_lan_contract.py", "lan_control")
    _write_test_file(tests_root / "test_lan_discovery.py", "")
    _write_test_file(tests_root / "test_lan_runtime.py", "")
    _write_test_file(tests_root / "test_lan_control_routing.py", "")
    _write_test_file(tests_root / "test_lan_payload.py", "")

    errors = hacs_preflight._check_lan_contract_tests()

    assert any("LAN event push method constant" in error for error in errors)
    assert (
        "lan_contract.py missing property-control frame builder: "
        "build_set_properties_message"
    ) in errors
    assert (
        "lan_contract.py missing monotonic message id builder: LanMessageBuilder"
    ) in errors
    assert any("LAN property update model" in error for error in errors)
    assert any("LAN device toggle routing helper" in error for error in errors)
    assert any("LAN group write routing helper" in error for error in errors)
    assert any("LAN scene execution routing helper" in error for error in errors)
    assert any("LAN numeric group route coverage" in error for error in errors)
    assert any("LAN cloud scene id fallback coverage" in error for error in errors)
    assert any("gateway_post.prop adapter" in error for error in errors)
    assert any("gateway_post.event adapter" in error for error in errors)
    assert any("invalid payload rejection" in error for error in errors)
    assert any("LAN event privacy filter" in error for error in errors)
    assert any("must remain no-network" in error for error in errors)
    assert (
        "lan_methods.py must remain no-network: socket"
    ) in errors
    assert any("UDP discovery runtime helper" in error for error in errors)
    assert any("UDP broadcast enable flag" in error for error in errors)
    assert any("hostless LAN discovery fallback" in error for error in errors)
    assert any("UDP discovery runtime coverage" in error for error in errors)
    assert any("LAN hostless discovery fallback coverage" in error for error in errors)
    assert any("gateway discovery text coverage" in error for error in errors)
    assert any("CRLF frame encoder coverage" in error for error in errors)
    assert any("LAN event privacy coverage" in error for error in errors)
    assert any("access token redaction coverage" in error for error in errors)
    assert any("documented approach event alias coverage" in error for error in errors)

def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
