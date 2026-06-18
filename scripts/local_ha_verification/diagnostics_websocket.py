"""Installed WebSocket-only event runtime verification."""

from __future__ import annotations

import ast
from pathlib import Path

from .report import VerificationReport

REQUIRED_WEBSOCKET_EVENT_RUNTIME_TOKENS = {
    "live_runtime.py": {
        "YeelightPushWebSocketTransport",
        "PushManager",
        "CONF_LIVE_UPDATES",
        "async_start_live_runtime",
    },
    "push_contract.py": {
        "DEFAULT_PUSH_BASE_URL",
        "wss://push.yeelight.com/ws",
        "PUSH_HEARTBEAT_INTERVAL_SECONDS = 20",
        "PUSH_HEARTBEAT_TIMEOUT_SECONDS = 60",
        "PUSH_EVENT_NOTIFICATION_TRANSPORT",
        "PUSH_CONTROL_METHODS",
        "PUSH_DATA_TYPES",
        "build_push_url",
        "build_subscribe_message",
        "build_heartbeat_message",
    },
    "push_transport.py": {
        "PushWebSocketSession",
        "next_subscribe",
        "next_heartbeat",
        "last_start_error_type",
        "last_runtime_error_type",
        "last_handshake_status",
        "last_disconnect_reason",
        "PushControlFrameError",
        "PushTransportConnectionMixin",
        "PushTransportRuntimeMixin",
        "PushTransportReconnectMixin",
    },
    "push_transport_connection.py": {
        "PushTransportConnectionMixin",
        "ws_connect",
        "websocket_ip_fallback",
        "enable_ip_fallback",
    },
    "push_transport_reconnect.py": {
        "PushTransportReconnectMixin",
        "_schedule_reconnect",
        "_reconnect_until_connected",
    },
    "push_transport_runtime.py": {
        "PushTransportRuntimeMixin",
        "_cleanup_after_reader_exit",
        "json_payload_from_message",
        "abnormal_close_before_first_frame",
    },
    "push_transport_dns.py": {
        "websocket_ip_fallback",
        "198.18.0.0/15",
        "resolve_public_dns_ips",
    },
    "push_transport_frames.py": {
        "PUSH_DATA_TYPES",
        "PUSH_CONTROL_METHODS",
        "is_push_data_payload",
        "PushControlFrameError",
    },
    "push_manager.py": {
        "PushManager",
        "PushTransport",
        "last_start_error_type",
        "last_runtime_error_type",
        "_sync_transport_runtime_error",
        "last_error_type",
    },
    "core/coordinator_runtime.py": {
        "async_handle_push_payload",
        "push_property_updates",
        "push_event_payloads",
        "dispatch_event_payloads",
        "async_update_listeners",
    },
}
FORBIDDEN_WEBSOCKET_EVENT_RUNTIME_TOKENS = {
    "SSE": "SSE runtime path",
    "EventSource": "EventSource runtime path",
    "Server-Sent": "Server-Sent Events runtime path",
    "server_sent": "Server-Sent Events runtime helper",
    "text/event-stream": "SSE content-type runtime path",
    "aiohttp_sse": "SSE dependency/runtime path",
    "sseclient": "SSE dependency/runtime path",
    "sse_consumer": "SSE consumer runtime path",
}


def verify_websocket_event_runtime_contract(
    install_root: Path,
    report: VerificationReport,
) -> None:
    """Verify installed event notifications are implemented through WebSocket."""
    missing_files: list[str] = []
    missing_tokens: list[str] = []
    forbidden_tokens: list[str] = []
    missing_call_edges: list[str] = []

    for relative_path, tokens in REQUIRED_WEBSOCKET_EVENT_RUNTIME_TOKENS.items():
        path = install_root / relative_path
        if not path.exists():
            missing_files.append(relative_path)
            continue
        content = path.read_text(encoding="utf-8")
        missing_tokens.extend(
            f"{relative_path}: {token}" for token in tokens if token not in content
        )
        forbidden_tokens.extend(
            f"{relative_path}: {reason}"
            for token, reason in FORBIDDEN_WEBSOCKET_EVENT_RUNTIME_TOKENS.items()
            if token in content
        )

    missing_call_edges.extend(_missing_websocket_runtime_call_edges(install_root))
    if missing_files:
        report.fail(
            "installed WebSocket event runtime missing files: "
            f"{missing_files}"
        )
    if missing_tokens:
        report.fail(
            "installed WebSocket event runtime missing tokens: "
            f"{missing_tokens}"
        )
    if forbidden_tokens:
        report.fail(
            "installed WebSocket event runtime contains forbidden non-WebSocket "
            f"tokens: {forbidden_tokens}"
        )
    if missing_call_edges:
        report.fail(
            "installed WebSocket event runtime missing call edges: "
            f"{missing_call_edges}"
        )
    if (
        not missing_files
        and not missing_tokens
        and not forbidden_tokens
        and not missing_call_edges
    ):
        report.fact("WebSocket-only event runtime contract present")
    report.metric(
        "websocket_event_runtime",
        {
            "required_files": len(REQUIRED_WEBSOCKET_EVENT_RUNTIME_TOKENS),
            "missing_files": len(missing_files),
            "missing_tokens": len(missing_tokens),
            "forbidden_tokens": len(forbidden_tokens),
            "missing_call_edges": len(missing_call_edges),
        },
    )


def _missing_websocket_runtime_call_edges(install_root: Path) -> list[str]:
    """Return missing AST call edges for the WebSocket-only event runtime."""
    live_tree = _parse_installed_module(install_root / "live_runtime.py")
    connection_tree = _parse_installed_module(install_root / "push_transport_connection.py")
    missing: list[str] = []
    if live_tree is None:
        missing.append("live_runtime.py: parseable AST")
    else:
        for call_name in ("YeelightPushWebSocketTransport", "PushManager"):
            if not _ast_has_call(live_tree, call_name):
                missing.append(f"live_runtime.py: {call_name}()")

    if connection_tree is None:
        missing.append("push_transport_connection.py: parseable AST")
    elif not _ast_has_attribute_call(connection_tree, "ws_connect"):
        missing.append("push_transport_connection.py: *.ws_connect()")
    return missing


def _parse_installed_module(path: Path) -> ast.AST | None:
    """Parse an installed Python module without importing it."""
    if not path.exists():
        return None
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _ast_has_call(tree: ast.AST, call_name: str) -> bool:
    """Return whether an AST calls a named constructor or function."""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == call_name
        for node in ast.walk(tree)
    )


def _ast_has_attribute_call(tree: ast.AST, attribute_name: str) -> bool:
    """Return whether an AST calls any object attribute with the given name."""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attribute_name
        for node in ast.walk(tree)
    )
