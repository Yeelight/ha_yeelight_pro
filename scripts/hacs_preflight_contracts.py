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
                errors.append(
                    f"{relative_path} exposes forbidden {reason}: {token}"
                )
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
    return errors


def check_oauth_contract_tests(component_root: Path) -> list[str]:
    """Ensure OAuth contract helpers stay no-network and explicit."""
    errors: list[str] = []
    required_files = {
        "oauth_contract.py": {
            "DEFAULT_OAUTH_AUTHORIZE_URL": "authorization endpoint constant",
            "DEFAULT_OAUTH_TOKEN_URL": "token endpoint constant",
            "build_authorization_url": "authorization URL builder",
            "build_authorization_code_token_body": "authorization-code body builder",
            "build_refresh_token_body": "refresh-token body builder",
            "parse_oauth_token_response": "token response parser",
            "raise_for_body_error": "shared Open API error classification",
        },
        "scan_login_contract.py": {
            "CLOUD_REGION_BASE_DOMAINS": "scan-login regional account domains",
            "SCAN_LOGIN_QRCODE_TTL_MS": "documented QR code TTL",
            "build_scan_login_qrcode_path": "QR-code creation path builder",
            "build_scan_login_status_path": "QR-code polling path builder",
            "build_scan_login_qrcode_content": "APP QR content builder",
            "parse_scan_login_response": "scan-login response parser",
        },
        "config_flow_scan_login.py": {
            "async_poll_scan_login_until_login": "continuous scan-login polling helper",
            "async_show_progress": "Home Assistant progress flow polling",
            "QrCodeSelector": "Home Assistant native QR-code selector",
            "QrCodeSelectorConfig": "QR-code selector configuration",
            "CONF_SCAN_LOGIN_QRCODE": "scan-login QR-code form field",
            "cloud_scan_login_schema_for_qrcode": "QR-code schema builder",
        },
        "tests/test_oauth_contract.py": {
            "build_authorization_url": "authorization URL coverage",
            "OAUTH_GRANT_AUTHORIZATION_CODE": "authorization-code grant coverage",
            "OAUTH_GRANT_REFRESH_TOKEN": "refresh-token grant coverage",
            "parse_oauth_token_response": "token parser coverage",
            "raise_for_oauth_error": "OAuth error classifier coverage",
            "secret-refresh-token": "redaction regression marker",
        },
        "tests/test_scan_login_contract.py": {
            "test_account_base_url_matches_documented_regions": (
                "regional account domain coverage"
            ),
            "build_scan_login_qrcode_content": "QR content coverage",
            "SCAN_LOGIN_QRCODE_TTL_MS": "5-minute QR TTL coverage",
            "parse_scan_login_response": "scan-login parser coverage",
            "secret-scan-token": "scan-login redaction marker",
        },
        "core/oauth.py": {
            "DEFAULT_OAUTH_TOKEN_URL": "OAuth token endpoint runtime",
            "exchange_authorization_code": "authorization-code runtime method",
            "refresh_oauth_token": "refresh-token runtime method",
            "parse_oauth_token_response": "shared OAuth token parser use",
        },
        "core/scan_login.py": {
            "account_base_url": "scan-login account endpoint runtime",
            "create_scan_login_qrcode": "QR-code creation runtime method",
            "check_scan_login_qrcode": "QR-code polling runtime method",
            "parse_scan_login_response": "shared scan-login parser use",
        },
        "tests/test_p0_oauth_runtime.py": {
            "exchange_authorization_code": "authorization-code client coverage",
            "refresh_oauth_token": "refresh-token client coverage",
            "Invalid refresh token": "documented refresh error coverage",
            "secret-refresh": "OAuth redaction regression marker",
        },
        "tests/test_scan_login_runtime.py": {
            "create_scan_login_qrcode": "scan-login QR runtime coverage",
            "check_scan_login_qrcode": "scan-login polling coverage",
            "FakeScanLoginSession": "shared scan-login fake coverage",
            "secret-scan-token": "scan-login runtime redaction marker",
        },
    }

    _require_tokens(component_root, required_files, errors, "OAuth contract requires")
    _check_no_network(component_root, ("oauth_contract.py", "scan_login_contract.py"), errors)
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
    _check_no_network(component_root, ("lan_methods.py", "lan_contract.py", "lan_payload.py"), errors)
    return errors


def check_analytics_contract_tests(component_root: Path) -> list[str]:
    """Ensure data-analysis API contracts stay no-network and explicit."""
    errors: list[str] = []
    required_files = {
        "analytics_contract.py": {
            "ANALYTICS_ALARM_ANALYSE": "alarm analyse endpoint key",
            "ANALYTICS_ALARM_TOP": "alarm top endpoint key",
            "ANALYTICS_ALARM_TREND": "alarm trend endpoint key",
            "ANALYTICS_ENERGY_ANALYSE": "energy analyse endpoint key",
            "ANALYTICS_ENERGY_TREND": "energy trend endpoint key",
            "ANALYTICS_ACTION_DAY": "daily action endpoint key",
            "ANALYTICS_ACTION_MONTH": "monthly action endpoint key",
            "ANALYTICS_ACTION_YEAR": "yearly action endpoint key",
            "ANALYTICS_METHOD_POST": "documented analytics POST method",
            "analytics_method": "analytics method helper",
            "analytics_request_path": "complete analytics path builder",
            "area_supported": "documented areaId boundary",
        },
        "tests/test_analytics_contract.py": {
            "test_analytics_paths_match_documented_endpoints": (
                "analytics path coverage"
            ),
            "alarm/analyse": "alarm analyse path coverage",
            "alarm/top": "alarm top path coverage",
            "alarm/trend": "alarm trend path coverage",
            "energy/analyse": "energy analyse path coverage",
            "energy/trend": "energy trend path coverage",
            "action/r/day": "daily action path coverage",
            "action/r/month": "monthly action path coverage",
            "action/r/year": "yearly action path coverage",
            "test_analytics_methods_match_documented_post_contract": (
                "analytics method coverage"
            ),
            "test_action_analytics_query_uses_documented_date_shape": (
                "action date shape coverage"
            ),
            "test_analytics_query_rejects_wrong_shape_or_unsupported_area": (
                "analytics date/area boundary coverage"
            ),
        },
    }

    _require_tokens(component_root, required_files, errors, "analytics contract requires")
    _check_no_network(component_root, ("analytics_contract.py",), errors)
    return errors


def _require_tokens(
    component_root: Path,
    required_files: dict[str, dict[str, str]],
    errors: list[str],
    missing_prefix: str,
) -> None:
    """Append missing-file and missing-token errors for release contracts."""
    for relative_path, required_tokens in required_files.items():
        path = component_root / relative_path
        if not path.exists():
            errors.append(f"{missing_prefix} {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"{relative_path} missing {reason}: {token}")


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
