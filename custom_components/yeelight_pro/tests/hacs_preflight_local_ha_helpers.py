"""Shared helpers for local HA preflight contract tests."""

from __future__ import annotations

from pathlib import Path


def _write_local_ha_contract_fixture(
    scripts_root: Path,
    local_ha_root: Path,
    tests_root: Path,
) -> None:
    """Write an intentionally weakened local-HA contract fixture."""
    _write_test_file(
        scripts_root / "verify_local_ha.py",
        "scripts.local_ha_verification.cli",
    )
    _write_test_file(local_ha_root / "install.py", "runtime_diff")
    _write_test_file(local_ha_root / "storage.py", "verify_storage")
    _write_test_file(local_ha_root / "storage_entries.py", "")
    _write_test_file(local_ha_root / "services.py", "verify_services")
    _write_test_file(local_ha_root / "runtime.py", "verify_logs")
    _write_test_file(
        local_ha_root / "diagnostics.py",
        (
            "DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES "
            "DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES "
            "DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES "
            "verify_diagnostics_capabilities diagnostics_capabilities "
            "verify_websocket_event_runtime_contract"
        ),
    )
    _write_test_file(local_ha_root / "diagnostics_websocket.py", "")
    _write_test_file(local_ha_root / "constants.py", "BAD_LOG_MARKERS")
    _write_test_file(local_ha_root / "cli.py", "build_parser")
    _write_test_file(scripts_root / "check_release_zip.py", "REQUIRED_FILES")
    _write_test_file(scripts_root / "hacs_preflight_claims.py", "STALE_DOC_CLAIMS")
    _write_test_file(scripts_root / "hacs_preflight_release_files.py", "")
    _write_test_file(
        scripts_root / "hacs_preflight_local_ha_release.py",
        (
            "LOCAL_HA_RELEASE_CONTRACT_TOKENS "
            "hacs_preflight_claims.py "
            "hacs_preflight_core.py "
            "hacs_preflight_local_ha_split_contracts.py "
            "hacs_preflight_split_contracts.py "
            "hacs_preflight_release_files.py "
            "hacs_preflight_lifecycle.py "
            "hacs_preflight_local_ha_protocol_contracts.py "
            "hacs_preflight_local_ha_probes.py "
            "scripts/verify_push_websocket.py "
            "tests/test_verify_push_websocket.py "
            "scripts/verify_scan_login.py "
            "tests/test_verify_scan_login.py "
            "scripts/verify_cloud_devices.py "
            "tests/test_verify_cloud_devices.py "
            "hacs_preflight_local_ha_runtime_sources.py "
            "hacs_preflight_local_ha_runtime_verifier_sources.py "
            "hacs_preflight_local_ha_runtime_core_tests.py "
            "hacs_preflight_local_ha_runtime_tests.py "
            "hacs_preflight_local_ha_runtime_verifier_tests.py"
        ),
    )
    _write_test_file(
        scripts_root / "hacs_preflight_local_ha_protocol_contracts.py",
        (
            "LOCAL_HA_PROTOCOL_CONTRACT_TOKENS "
            "hacs_preflight_scan_login_contracts.py "
            "hacs_preflight_push_contracts.py"
        ),
    )
    _write_test_file(
        scripts_root / "hacs_preflight_contracts.py",
        "check_push_contract_tests",
    )
    _write_test_file(
        scripts_root / "hacs_preflight_scan_login_contracts.py",
        "check_scan_login_contract_tests",
    )
    _write_test_file(
        scripts_root / "hacs_preflight_push_contracts.py",
        "PUSH_CONTRACT_REQUIRED_FILES",
    )
    _write_test_file(
        scripts_root / "hacs_preflight_local_ha_runtime_verifier_sources.py",
        "",
    )
    _write_test_file(scripts_root / "hacs_preflight_local_ha_probes.py", "")
    _write_test_file(scripts_root / "verify_cloud_devices.py", "")
    _write_test_file(scripts_root / "verify_push_websocket.py", "")
    _write_test_file(scripts_root / "verify_scan_login.py", "")
    _write_test_file(scripts_root / "verify_local_ha_recovery.py", "")
    _write_test_file(scripts_root / "verify_local_ha_soak.py", "")
    _write_test_file(scripts_root.parent / "test_actual_environment.py", "")
    _write_test_file(scripts_root.parent / "test_complete_ha.py", "")
    _write_test_file(scripts_root.parent / "test_functional.py", "")
    _write_test_file(scripts_root.parent / "test_real_ha_environment.py", "")
    _write_test_file(scripts_root / "hacs_preflight_runtime_options.py", "")
    _write_test_file(scripts_root / "hacs_preflight_core.py", "check_exists")
    _write_test_file(
        scripts_root / "hacs_preflight_split_contracts.py",
        (
            "SPLIT_CONTRACT_TEST_TOKENS "
            "SPLIT_CLIENT_CONTRACT_TEST_TOKENS "
            "_SPLIT_CONFIG_FLOW_CONTRACT_TEST_TOKENS "
            "test_capability_registry_contract.py "
            "test_options_flow_contract.py "
            "test_translation_runtime_contract.py"
        ),
    )
    _write_test_file(
        scripts_root / "hacs_preflight_split_client_contracts.py",
        "SPLIT_CLIENT_CONTRACT_TEST_TOKENS",
    )
    _write_test_file(
        scripts_root / "hacs_preflight_local_ha_split_contracts.py",
        (
            "LOCAL_HA_SPLIT_CONTRACT_TOKENS "
            "hacs_preflight_split_contracts.py "
            "hacs_preflight_split_client_contracts.py"
        ),
    )
    _write_test_file(
        scripts_root / "hacs_preflight_lifecycle.py",
        "LIFECYCLE_CONTRACT_TOKENS async_remove_config_entry_device",
    )
    _write_test_file(tests_root / "test_verify_local_ha.py", "runtime_diff")
    _write_test_file(tests_root / "test_verify_local_ha_runtime.py", "verify_logs")
    _write_test_file(tests_root / "test_verify_local_ha_storage.py", "verify_storage")
    _write_test_file(
        tests_root / "test_verify_local_ha_diagnostics.py",
        (
            "test_verify_diagnostics_capabilities_accepts_release_boundaries "
            "test_verify_diagnostics_capabilities_rejects_enabled_live_flag "
            "test_verify_diagnostics_capabilities_rejects_removed_oauth_flag "
            "test_verify_diagnostics_capabilities_requires_literal_flags"
        ),
    )
    _write_test_file(
        tests_root / "local_ha_diagnostics_verifier_helpers.py",
        "write_websocket_event_runtime",
    )
    _write_test_file(tests_root / "test_verify_local_ha_websocket_runtime.py", "")
    _write_test_file(tests_root / "test_verify_local_ha_schema_cache.py", "")
    _write_test_file(tests_root / "test_verify_push_websocket.py", "")
    _write_test_file(tests_root / "test_verify_cloud_devices.py", "")
    _write_test_file(tests_root / "test_verify_scan_login.py", "")
    _write_test_file(tests_root / "test_verify_local_ha_recovery.py", "")
    _write_test_file(tests_root / "test_verify_local_ha_soak.py", "")
    _write_test_file(tests_root / "test_legacy_local_ha_entrypoints.py", "")
    _write_test_file(tests_root / "test_schema_cache.py", "")
    _write_test_file(tests_root / "test_schema_cache_logging.py", "")
    _write_test_file(tests_root / "test_coordinator_topology.py", "")
    _write_test_file(tests_root / "test_coordinator_topology_diff.py", "")
    _write_test_file(tests_root / "test_hacs_preflight_release_quality.py", "")
    _write_test_file(tests_root / "test_hacs_preflight_runtime_options.py", "")
    _write_test_file(tests_root / "test_entity_lifecycle_reconcile.py", "")
    _write_test_file(tests_root / "test_registry_cleanup_service.py", "")
    _write_test_file(tests_root.parent / "entry_migration.py", "")
    _write_test_file(tests_root.parent / "device_filter.py", "")
    _write_test_file(tests_root.parent / "config_flow_helpers.py", "")
    _write_test_file(tests_root.parent / "config_flow_options.py", "")
    (tests_root.parent / "core").mkdir()
    _write_test_file(tests_root.parent / "core" / "schema_cache.py", "")
    _write_test_file(tests_root / "test_entry_migration.py", "")
    _write_test_file(tests_root / "test_entry_options_migration.py", "")


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
