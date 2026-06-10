"""APP scan-login release-preflight contract tokens."""

from __future__ import annotations

from pathlib import Path

from scripts.hacs_preflight_contracts import _check_no_network, _require_tokens


def check_scan_login_contract_tests(component_root: Path) -> list[str]:
    """Ensure APP scan-login helpers stay no-network and explicit."""
    errors: list[str] = []
    required_files = {
        "scan_login_contract.py": {
            "CLOUD_REGION_BASE_DOMAINS": "scan-login regional account domains",
            "SCAN_LOGIN_QRCODE_TTL_MS": "documented QR code TTL",
            "YeelightAccountToken": "scan-login token model",
            "_QR_CODE_ID_FIELDS": "scan-login QR field alias coverage",
            "_ACCESS_TOKEN_FIELDS": "scan-login token field alias coverage",
            "_REFRESH_TOKEN_FIELDS": "scan-login refresh-token field alias coverage",
            "_first_value": "scan-login field alias helper",
            "build_scan_login_qrcode_path": "QR-code creation path builder",
            "build_scan_login_status_path": "QR-code polling path builder",
            "build_scan_login_qrcode_content": "APP QR content builder",
            "cli&": "APP-supported QR payload prefix",
            "parse_scan_login_response": "scan-login response parser",
            "_expire_at_ms": "QR countdown expiry derivation helper",
        },
        "config_flow_scan_login.py": {
            "async_poll_scan_login_until_login": (
                "continuous scan-login polling helper"
            ),
            "async_show_progress": "Home Assistant progress flow polling",
        },
        "config_flow_scan_login_helpers.py": {
            "async_poll_scan_login_until_login": (
                "continuous scan-login polling helper"
            ),
            "async_scan_login_device_id": "scan-login HA instance device helper",
            "instance_id.async_get": "HA instance id source for scan-login device",
            "hashlib.sha256": "scan-login device hash derivation",
            'f"ha-{digest}"': "scan-login device prefix boundary",
            "QrCodeSelector": "Home Assistant native QR-code selector",
            "QrCodeSelectorConfig": "QR-code selector configuration",
            "CONF_SCAN_LOGIN_QRCODE": "scan-login QR-code form field",
            "cloud_scan_login_schema_for_qrcode": "QR-code schema builder",
        },
        "tests/test_scan_login_contract.py": {
            "test_account_base_url_matches_documented_regions": (
                "regional domain coverage"
            ),
            "build_scan_login_qrcode_content": "QR content coverage",
            "cli&AA:BB:CC:DD:EE:FF&qr-1": "APP QR payload order coverage",
            "SCAN_LOGIN_QRCODE_TTL_MS": "5-minute QR TTL coverage",
            "parse_scan_login_response": "scan-login parser coverage",
            "test_parse_scan_login_response_derives_expire_at_for_countdown": (
                "QR countdown expiry derivation coverage"
            ),
            "test_parse_scan_login_created_response_accepts_snake_case_aliases": (
                "QR alias coverage"
            ),
            "test_parse_scan_login_login_response_accepts_token_field_aliases": (
                "token alias coverage"
            ),
            "secret-scan-token": "scan-login redaction marker",
        },
        "core/scan_login.py": {
            "account_base_url": "scan-login account endpoint runtime",
            "create_scan_login_qrcode": "QR-code creation runtime method",
            "check_scan_login_qrcode": "QR-code polling runtime method",
            "parse_scan_login_response": "shared scan-login parser use",
        },
        "tests/test_scan_login_runtime.py": {
            "create_scan_login_qrcode": "scan-login QR runtime coverage",
            "check_scan_login_qrcode": "scan-login polling coverage",
            "FakeScanLoginSession": "shared scan-login fake coverage",
            "secret-scan-token": "scan-login runtime redaction marker",
        },
        "tests/test_config_flow_scan_login_device.py": {
            "test_scan_login_device_id_hashes_ha_instance_id_without_leaking_raw_id": (
                "scan-login device id privacy coverage"
            ),
            "test_scan_login_device_id_changes_for_different_ha_instance_ids": (
                "scan-login device id uniqueness coverage"
            ),
            "raw-instance-secret": "raw HA instance id leakage regression marker",
        },
        "tests/test_config_flow_scan_login.py": {
            "test_cloud_scan_login_initial_step_creates_qrcode": (
                "scan-login qrcode creation coverage"
            ),
            'selector_type == "qr_code"': "native Home Assistant QR selector coverage",
            "CONF_SCAN_LOGIN_QRCODE": "scan-login QR selector field coverage",
            "test_cloud_scan_login_submit_starts_continuous_progress_poll": (
                "scan-login progress polling coverage"
            ),
            "test_cloud_scan_login_progress_done_loads_houses": (
                "scan-login LOGIN token flow coverage"
            ),
            "test_cloud_scan_login_rejects_different_region": (
                "initial scan-login region isolation coverage"
            ),
            "test_cloud_scan_login_expired_qrcode_requires_manual_refresh": (
                "scan-login expired QR manual refresh coverage"
            ),
            "test_cloud_scan_login_poll_timeout_returns_expired_error": (
                "scan-login polling timeout UX coverage"
            ),
            "CONF_SCAN_LOGIN_REFRESH": "scan-login qrcode refresh form coverage",
        },
        "tests/test_verify_scan_login.py": {
            "test_validate_run_request_requires_explicit_confirm": (
                "production scan-login confirm guard coverage"
            ),
            "test_validate_run_request_requires_device_env": (
                "production scan-login device env guard coverage"
            ),
            "test_validate_run_request_rejects_invalid_region_and_unbounded_probe": (
                "production scan-login bounded-run guard coverage"
            ),
            "test_summary_redacts_qr_device_token_and_user_values": (
                "production scan-login redacted summary coverage"
            ),
            "test_main_does_not_probe_network_without_confirm": (
                "production scan-login default no-network coverage"
            ),
            "test_script_path_execution_is_no_network_without_confirm": (
                "production scan-login script-path no-network coverage"
            ),
            "test_probe_summarizes_created_scanned_login_without_values": (
                "production scan-login fake-login aggregate coverage"
            ),
            "test_main_can_show_qrcode_only_after_explicit_confirm": (
                "production scan-login explicit QR display coverage"
            ),
        },
        "scripts/verify_scan_login.py": {
            "confirm-production-scan-login": (
                "explicit production scan-login confirm flag"
            ),
            "YEELIGHT_PRO_SCAN_LOGIN_DEVICE": (
                "environment-only scan-login device input"
            ),
            "validate_run_request": "production scan-login fail-closed safety gate",
            "ScanLoginProbeSummary": "diagnostics-safe scan-login probe summary",
            "async_probe_scan_login": "explicit production scan-login entrypoint",
            "show_qrcode": "explicit scan-login QR display switch",
            "_print_qrcode_event": "manual scan-login QR event output",
            "SCAN_LOGIN_CONTRACT_PATH": (
                "Home Assistant-free scan-login contract path"
            ),
            "_load_scan_login_contract": (
                "Home Assistant-free scan-login contract loader"
            ),
            "build_scan_login_qrcode_path": "documented QR-code path helper reuse",
            "build_scan_login_status_path": (
                "documented QR-code status path helper reuse"
            ),
            "parse_scan_login_response": "shared scan-login parser reuse",
        },
    }

    _require_tokens(component_root, required_files, errors, "scan-login contract requires")
    _check_no_network(component_root, ("scan_login_contract.py",), errors)
    return errors


__all__ = ["check_scan_login_contract_tests"]
