"""Shared fixtures for local HA diagnostics verifier tests."""

from __future__ import annotations

from pathlib import Path


def install_root(config_dir: Path) -> Path:
    """Create a minimal installed component root."""
    root = config_dir / "custom_components" / "yeelight_pro"
    root.mkdir(parents=True)
    return root


def write_diagnostics(
    root: Path,
    *,
    mqtt_subscription: bool = False,
    include_ambiguous_oauth: bool = False,
) -> None:
    """Write minimal diagnostics.py capability flags."""
    ambiguous_oauth = (
        '        "oauth_authorization_code_flow": True,\n'
        if include_ambiguous_oauth
        else ""
    )
    root.joinpath("diagnostics.py").write_text(
        f"""
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
        "websocket_transport_runtime": True,
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "push_connection": True,
        "websocket_subscription": True,
        "websocket_event_notifications": True,
        "local_gateway_control": True,
        "lan_control": True,
        "mqtt_subscription": {mqtt_subscription},
    }}
""",
        encoding="utf-8",
    )


def write_diagnostic_payloads(
    root: Path,
    *,
    include_scan_login_device: bool = True,
) -> None:
    """Write minimal diagnostic_payloads.py redaction contract."""
    redaction_entry = "CONF_SCAN_LOGIN_DEVICE,\n" if include_scan_login_device else ""
    root.joinpath("diagnostic_payloads.py").write_text(
        f"""
CONF_ACCESS_TOKEN = "access_token"
CONF_SCAN_LOGIN_DEVICE = "scan_login_device"
TO_REDACT = {{
    CONF_ACCESS_TOKEN,
    {redaction_entry.rstrip()}
}}
""",
        encoding="utf-8",
    )


def write_websocket_event_runtime(
    root: Path,
    *,
    include_transport: bool = True,
    include_eventsource: bool = False,
    include_runtime_health: bool = True,
    include_live_transport_call: bool = True,
    include_ws_connect_call: bool = True,
) -> None:
    """Write minimal installed WebSocket event runtime files."""
    (root / "core").mkdir()
    live_call = (
        '    return PushManager(coordinator, YeelightPushWebSocketTransport(session=hass, token="token"))'
        if include_live_transport_call
        else "    return PushManager(coordinator, None)"
    )
    root.joinpath("live_runtime.py").write_text(
        f"""
CONF_LIVE_UPDATES = "live_updates"
class YeelightPushWebSocketTransport: ...
class PushManager: ...
async def async_start_live_runtime(hass, entry, coordinator):
{live_call}
""",
        encoding="utf-8",
    )
    root.joinpath("push_contract.py").write_text(
        """
DEFAULT_PUSH_BASE_URL = "wss://push.yeelight.com/ws"
PUSH_HEARTBEAT_INTERVAL_SECONDS = 20
PUSH_HEARTBEAT_TIMEOUT_SECONDS = 60
PUSH_EVENT_NOTIFICATION_TRANSPORT = "WebSocket"
PUSH_CONTROL_METHODS = frozenset({"subscribe", "heartbeat"})
PUSH_DATA_TYPES = frozenset({"prop", "event"})
def build_push_url(token): ...
def build_subscribe_message(message_id): ...
def build_heartbeat_message(message_id): ...
""",
        encoding="utf-8",
    )
    if include_transport:
        eventsource = (
            'class SSETransport: ...\nEventSource("https://example.test/events")'
            if include_eventsource
            else ""
        )
        runtime_health = (
            """
last_start_error_type = None
last_runtime_error_type = None
class PushControlFrameError(Exception): ...
"""
            if include_runtime_health
            else ""
        )
        connect_line = (
            '        return await self._session.ws_connect("wss://push.yeelight.com/ws/token")'
            if include_ws_connect_call
            else "        return None"
        )
        root.joinpath("push_transport.py").write_text(
            f"""
class PushWebSocketSession:
    async def ws_connect(self, url): ...
class YeelightPushWebSocketTransport:
    async def _connect_once(self):
{connect_line}
PUSH_CONTROL_METHODS = object()
PUSH_DATA_TYPES = object()
def next_subscribe(): ...
def next_heartbeat(): ...
def _is_push_data_payload(payload):
    return payload.get("type") in PUSH_DATA_TYPES
{runtime_health}
{eventsource}
""",
            encoding="utf-8",
        )
    manager_health = (
        """
last_start_error_type = None
last_runtime_error_type = None
last_error_type = None
def _sync_transport_runtime_error(): ...
"""
        if include_runtime_health
        else ""
    )
    root.joinpath("push_manager.py").write_text(
        f"""
class PushTransport: ...
class PushManager: ...
{manager_health}
""",
        encoding="utf-8",
    )
    root.joinpath("core", "coordinator_runtime.py").write_text(
        """
def push_property_updates(payload): ...
def push_event_payloads(payload): ...
class CoordinatorRuntimeMixin:
    async def async_handle_push_payload(self, payload):
        push_property_updates(payload)
        push_event_payloads(payload)
        self.async_update_listeners()
        return await bridge.dispatch_event_payloads([])
""",
        encoding="utf-8",
    )


def write_diagnostic_options(
    root: Path,
    *,
    include_scan_interval: bool = True,
    include_normalize_token: bool = True,
) -> None:
    """Write minimal diagnostic_options.py option_status contract."""
    normalize_token = (
        "normalize_entry_options(entry_options)\n"
        if include_normalize_token
        else "dict(entry_options)\n"
    )
    scan_field = (
        '        "scan_interval_seconds": 30,\n'
        if include_scan_interval
        else ""
    )
    root.joinpath("diagnostic_options.py").write_text(
        f"""
CONF_DEVICE_IMPORT_FILTER = "device_import_filter"

def option_status_diagnostics(entry, runtime, coordinator):
    entry_options = {{}}
    {normalize_token.rstrip()}
    return {{
        "debug_mode_enabled": False,
{scan_field.rstrip()}
        "live_updates_enabled": False,
        "local_gateway_control_enabled": False,
        "import_filter_active": bool(entry_options.get(CONF_DEVICE_IMPORT_FILTER)),
    }}
""",
        encoding="utf-8",
    )
