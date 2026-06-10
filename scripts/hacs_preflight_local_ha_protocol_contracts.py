"""Local HA release tokens for protocol preflight helpers."""

from __future__ import annotations

LOCAL_HA_PROTOCOL_CONTRACT_TOKENS = {
    "scripts/hacs_preflight_local_ha_protocol_contracts.py": {
        "LOCAL_HA_PROTOCOL_CONTRACT_TOKENS": "protocol contract token registry",
        "hacs_preflight_oauth_contracts.py": "OAuth contract token split coverage",
        "hacs_preflight_push_contracts.py": "push contract token split coverage",
    },
    "scripts/hacs_preflight_oauth_contracts.py": {
        "check_oauth_contract_tests": "OAuth contract preflight helper",
        "tests/test_verify_scan_login.py": "scan-login production test token guard",
        "scripts/verify_scan_login.py": "scan-login production probe script guard",
        "Home Assistant-free scan-login contract path": (
            "scan-login HA-free contract path guard"
        ),
        "Home Assistant-free scan-login contract loader": (
            "scan-login HA-free contract loader guard"
        ),
    },
    "scripts/hacs_preflight_push_contracts.py": {
        "PUSH_CONTRACT_REQUIRED_FILES": "push contract token registry",
        "PushReconnectPolicy": "push reconnect policy release guard",
        "tests/test_push_transport.py": "push transport test token guard",
        "tests/test_push_websocket_contract.py": (
            "WebSocket-only push contract test token guard"
        ),
        "tests/test_push_transport_failures.py": (
            "push transport failure test token guard"
        ),
        "tests/test_runtime_bridge_lan_events.py": (
            "runtime bridge LAN event test token guard"
        ),
        "scripts/verify_push_websocket.py": (
            "production WebSocket probe script token guard"
        ),
        "tests/test_verify_push_websocket.py": (
            "production WebSocket probe test token guard"
        ),
    },
}
