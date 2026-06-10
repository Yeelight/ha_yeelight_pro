"""Contract-level helpers for Yeelight Pro HACS preflight checks."""

from __future__ import annotations

from pathlib import Path

from scripts.hacs_preflight_push_contracts import PUSH_CONTRACT_REQUIRED_FILES

_NO_NETWORK_TOKENS = (
    "aiohttp",
    "create_datagram_endpoint",
    "open_connection",
    "requests",
    "socket",
)

_FORBIDDEN_OPEN_API_RUNTIME_TOKENS = {
    "/deliver/": "house transfer endpoint path",
    "deliver/{targetUid}": "house transfer documented path template",
    "house_transfer": "house transfer helper or service name",
    "transfer_house": "house transfer helper or service name",
    "deliver_house": "house transfer helper or service name",
    "targetUid": "house transfer target user id parameter",
    "家庭转移": "house transfer runtime label",
}
_FORBIDDEN_PUSH_RUNTIME_PROTOCOL_TOKENS = {
    "SSE": "SSE runtime path",
    "EventSource": "EventSource runtime path",
    "Server-Sent": "Server-Sent Events runtime path",
    "server_sent": "Server-Sent Events runtime helper",
    "text/event-stream": "SSE content-type runtime path",
    "aiohttp_sse": "SSE dependency/runtime path",
    "sseclient": "SSE dependency/runtime path",
    "sse_consumer": "SSE consumer runtime path",
}


def check_forbidden_open_api_runtime(component_root: Path) -> list[str]:
    """Block dangerous Open API endpoints from runtime modules."""
    errors: list[str] = []
    for path in sorted(component_root.rglob("*.py")):
        if "__pycache__" in path.parts or "tests" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(component_root.parent.parent)
        for token, reason in _FORBIDDEN_OPEN_API_RUNTIME_TOKENS.items():
            if token in content:
                errors.append(f"{relative_path} exposes forbidden {reason}: {token}")
    return errors


def check_websocket_only_push_runtime(component_root: Path) -> list[str]:
    """阻断 SSE/EventSource 运行时路径；易来推送只允许 WebSocket。"""
    errors: list[str] = []
    for path in sorted(component_root.rglob("*.py")):
        if "__pycache__" in path.parts or "tests" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(component_root.parent.parent)
        for token, reason in _FORBIDDEN_PUSH_RUNTIME_PROTOCOL_TOKENS.items():
            if token in content:
                errors.append(f"{relative_path} exposes forbidden {reason}: {token}")
    return errors


def check_push_contract_tests(component_root: Path) -> list[str]:
    """Ensure push protocol contracts stay explicit before release."""
    errors: list[str] = []
    _require_tokens(
        component_root,
        PUSH_CONTRACT_REQUIRED_FILES,
        errors,
        "push contract requires",
    )
    _check_no_network(component_root, ("push_contract.py", "core/runtime_bridge.py"), errors)
    errors.extend(check_websocket_only_push_runtime(component_root))
    return errors


def check_lan_contract_tests(component_root: Path) -> list[str]:
    """Ensure LAN protocol contracts stay no-network and explicit."""
    errors: list[str] = []
    required_files = {
        "lan_methods.py": {
            "METHOD_POST_PROP": "LAN property push method constant",
            "METHOD_POST_EVENT": "LAN event push method constant",
            "METHOD_SET_PROP": "LAN property-control method constant",
        },
        "lan_contract.py": {
            "LAN_DISCOVERY_MESSAGE": "UDP discovery message constant",
            "LAN_DISCOVERY_PORT": "UDP discovery port constant",
            "LAN_GATEWAY_PORT": "TCP gateway port constant",
            "parse_discovery_response": "discovery response parser",
            "encode_lan_frame": "CRLF frame encoder",
            "decode_lan_frames": "CRLF frame decoder",
            "build_set_properties_message": "property-control frame builder",
            "LanMessageBuilder": "monotonic message id builder",
            "is_lan_push_message": "gateway_post push classifier",
        },
        "lan_discovery.py": {
            "async_discover_lan_gateway": "UDP discovery runtime helper",
            "create_datagram_endpoint": "UDP discovery socket boundary",
            "allow_broadcast": "UDP broadcast enable flag",
            "parse_discovery_response": "discovery parser runtime use",
            "LAN_DISCOVERY_MESSAGE": "discovery message runtime use",
        },
        "lan_runtime.py": {
            "async_discover_lan_gateway": "hostless LAN discovery fallback",
            "Yeelight Pro LAN gateway host is required": "discovery failure guard",
        },
        "lan_payload.py": {
            "YeelightLanPropertyUpdate": "LAN property update model",
            "lan_property_updates": "gateway_post.prop adapter",
            "lan_event_payloads": "gateway_post.event adapter",
            "HomeAssistantError": "invalid payload rejection",
            "_SENSITIVE_EVENT_PARAM_KEYS": "LAN event privacy filter",
        },
        "core/lan_control.py": {
            "async_try_lan_control_device": "LAN device write routing helper",
            "async_try_lan_toggle_device": "LAN device toggle routing helper",
            "async_try_lan_control_group": "LAN group write routing helper",
            "async_try_lan_execute_scene": "LAN scene execution routing helper",
            "\"nt\": 2": "LAN device node type",
            "\"nt\": 4": "LAN group node type",
            "\"toggle\": list(properties)": "LAN toggle payload boundary",
            "scenes=[{\"id\": node_id, \"duration\": duration}]": (
                "LAN scene payload boundary"
            ),
            "except Exception": "LAN health unreadable fallback guard",
            "_lan_uint_id": "LAN numeric id fallback guard",
            "safe_error_summary": "LAN control redaction helper",
        },
        "core/coordinator_controls.py": {
            "CoordinatorControlMixin": "split coordinator control routing helper",
            "async_try_lan_control_device": "LAN-first device set route",
            "async_try_lan_toggle_device": "LAN-first device toggle route",
            "async_try_lan_control_group": "LAN-first group route",
            "async_try_lan_execute_scene": "LAN-first scene route",
            "async_execute_toggle_device": "cloud fallback toggle route",
            "async_execute_control_group": "cloud fallback group route",
            "async_execute_scene_command": "cloud fallback scene route",
        },
        "tests/test_lan_contract.py": {
            "YEELIGHT_GATEWAY_CONTROL_DISCOVER": "gateway discovery text coverage",
            "parse_discovery_response": "discovery parser coverage",
            "encode_lan_frame": "CRLF frame encoder coverage",
            "decode_lan_frames": "CRLF frame decoder coverage",
            "build_set_properties_message": "set prop frame coverage",
            "LanMessageBuilder": "message id increment coverage",
            "is_lan_push_message": "gateway_post push classifier coverage",
            "lan_control": "LAN diagnostics capability boundary coverage",
        },
        "tests/test_lan_discovery.py": {
            "async_discover_lan_gateway": "UDP discovery runtime coverage",
            "allow_broadcast": "UDP broadcast option coverage",
            "LAN_DISCOVERY_BROADCAST_HOST": "UDP broadcast address coverage",
            "ignores_invalid_response_until_timeout": (
                "invalid discovery response timeout coverage"
            ),
        },
        "tests/test_lan_runtime.py": {
            "test_start_lan_runtime_discovers_gateway_when_host_is_empty": (
                "LAN hostless discovery fallback coverage"
            ),
            "test_start_lan_runtime_requires_discovery_when_host_missing": (
                "LAN discovery miss failure coverage"
            ),
        },
        "tests/test_lan_control_routing.py": {
            "test_coordinator_toggle_device_uses_connected_lan_runtime": (
                "LAN toggle route coverage"
            ),
            "test_coordinator_toggle_device_falls_back_to_cloud_when_lan_disconnected": (
                "LAN toggle cloud fallback coverage"
            ),
            "test_coordinator_control_group_uses_connected_lan_for_numeric_group_id": (
                "LAN numeric group route coverage"
            ),
            "test_coordinator_control_group_falls_back_to_cloud_for_cloud_group_id": (
                "LAN cloud group id fallback coverage"
            ),
            "test_coordinator_execute_scene_uses_connected_lan_for_numeric_scene_id": (
                "LAN numeric scene route coverage"
            ),
            "test_coordinator_execute_scene_falls_back_to_cloud_for_cloud_scene_id": (
                "LAN cloud scene id fallback coverage"
            ),
            "test_coordinator_lan_group_control_error_is_redacted": (
                "LAN group error redaction coverage"
            ),
        },
        "tests/test_lan_payload.py": {
            "gateway_post.prop": "LAN property push adapter coverage",
            "gateway_post.event": "LAN event push adapter coverage",
            "gateway_set.prop": "outgoing control frame rejection coverage",
            "redact_sensitive_event_params": "LAN event privacy coverage",
            "access_token": "access token redaction coverage",
            "device_id": "device id redaction coverage",
            "panel.release": "documented release event alias coverage",
            "approach.true": "documented approach event alias coverage",
            "approach.false": "documented leave event alias coverage",
        },
    }

    _require_tokens(component_root, required_files, errors, "LAN contract requires")
    _check_no_network(
        component_root,
        ("lan_methods.py", "lan_contract.py", "lan_payload.py", "core/lan_control.py"),
        errors,
    )
    return errors


def _require_tokens(
    component_root: Path,
    required_files: dict[str, dict[str, str]],
    errors: list[str],
    missing_prefix: str,
) -> None:
    """Append missing-file and missing-token errors for release contracts."""
    for relative_path, required_tokens in required_files.items():
        path = _contract_path(component_root, relative_path)
        if not path.exists():
            errors.append(f"{missing_prefix} {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"{relative_path} missing {reason}: {token}")


def _contract_path(component_root: Path, relative_path: str) -> Path:
    """Resolve component-relative contracts plus root-level helper scripts."""
    if relative_path.startswith("scripts/"):
        return component_root.parent.parent / relative_path
    return component_root / relative_path


def _check_no_network(
    component_root: Path,
    relative_paths: tuple[str, ...],
    errors: list[str],
) -> None:
    """Append errors when pure LAN contract modules import transport primitives."""
    for relative_path in relative_paths:
        path = component_root / relative_path
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for token in _NO_NETWORK_TOKENS:
            if token in content:
                errors.append(f"{relative_path} must remain no-network: {token}")
