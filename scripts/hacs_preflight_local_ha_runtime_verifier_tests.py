"""Runtime verifier test contract tokens for local HA validation."""

from __future__ import annotations

LOCAL_HA_RUNTIME_VERIFIER_TEST_TOKENS = {
    "scripts/hacs_preflight_local_ha_runtime_verifier_tests.py": {
        "LOCAL_HA_RUNTIME_VERIFIER_TEST_TOKENS": (
            "runtime verifier test token registry"
        ),
        "test_verify_local_ha_runtime.py": "runtime verifier test coverage",
        "test_verify_local_ha_storage.py": "storage verifier test coverage",
        "test_verify_local_ha_storage_cleanup.py": (
            "storage cleanup verifier test coverage"
        ),
        "test_verify_local_ha_storage_quality.py": (
            "storage quality verifier test coverage"
        ),
        "test_verify_local_ha_schema_cache.py": "schema cache verifier test coverage",
        "test_verify_local_ha_config_entries.py": (
            "config-entry storage verifier test coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha.py": {
        "runtime_diff": "runtime drift unit coverage",
        "verify_required_modules": "installed support module presence coverage",
        "ha_device_registry": "HA device registry module presence coverage",
        "light_group": "group light runtime module presence coverage",
        "test_required_modules_include_config_flow_options_helper": (
            "config flow options helper module presence coverage"
        ),
        "test_required_modules_include_runtime_template_helpers": (
            "runtime template helper module presence coverage"
        ),
        "test_required_modules_include_protocol_contract_modules": (
            "protocol modules install-state coverage"
        ),
        "scan_login_contract": "scan-login contract install-state coverage",
        "push_contract": "push contract install-state coverage",
        "lan_contract": "LAN contract install-state coverage",
        "forbidden_install_paths": "forbidden install artifact coverage",
        "parse_domain_counts": "CLI expected count override coverage",
    },
    "custom_components/yeelight_pro/tests/test_sync_local_ha_runtime.py": {
        "test_iter_runtime_files_excludes_tests_and_generated_artifacts": (
            "safe local HA runtime sync coverage"
        ),
        "test_sync_script_fails_when_install_target_still_contains_tests": (
            "post-sync install hygiene failure coverage"
        ),
        "ha_device_registry.py": "new runtime module sync coverage",
        "text.py": "forbidden legacy text platform sync regression marker",
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_config_entries.py": {
        "verify_storage": "config-entry storage verifier coverage",
        "test_verify_storage_rejects_unmigrated_config_entry_version": (
            "config entry migration version coverage"
        ),
        "test_verify_storage_reports_missing_config_entry_keys_without_values": (
            "config entry required key redaction coverage"
        ),
        "test_verify_storage_allows_missing_optional_open_api_client_id": (
            "manual token optional client id coverage"
        ),
        "test_verify_storage_reports_defaulted_option_keys": (
            "config entry option default coverage"
        ),
        "test_verify_storage_rejects_invalid_option_values": (
            "config entry option bounds coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_storage.py": {
        "verify_storage": "aggregate storage coverage",
        "test_verify_storage_allows_cleanup_b_retained_disabled_entities": (
            "cleanup B retained registry coverage"
        ),
        "test_verify_storage_reports_platform_options_alignment": (
            "platform/options alignment coverage"
        ),
        "test_verify_storage_rejects_unsupported_platform_domain": (
            "unsupported platform domain coverage"
        ),
        "test_verify_storage_reports_missing_files_without_raw_payload": (
            "sanitized storage failure coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_storage_quality.py": {
        "test_verify_storage_rejects_source_devices_missing_registry_metadata": (
            "source-device registry metadata coverage"
        ),
        "test_verify_storage_rejects_chinese_generic_source_device_models": (
            "Chinese generic source-device model rejection coverage"
        ),
        "灯具": "Chinese light generic model fixture",
        "继电器开关": "Chinese relay-switch generic model fixture",
        "test_verify_storage_rejects_house_placeholder_device_names": (
            "house placeholder device-name rejection coverage"
        ),
        "generated house helper names": "house placeholder verifier failure message",
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_storage_entity_quality.py": {
        "test_verify_storage_rejects_device_backed_entities_without_device_id": (
            "device-backed entity registry coverage"
        ),
        "test_verify_storage_rejects_raw_numeric_entity_names": (
            "raw numeric channel/entity-name rejection coverage"
        ),
        "default duration": "raw English property-name fixture",
        "raw channel/action/property names": (
            "raw channel/action/property-name failure message"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_storage_restore_state.py": {
        "test_verify_storage_rejects_unavailable_yeelight_restore_states": (
            "Yeelight restore-state unavailable rejection coverage"
        ),
        "restored states are unavailable": (
            "Yeelight restore-state unavailable failure message"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_storage_cleanup.py": {
        "test_verify_storage_fails_for_enabled_legacy_scene_entities": (
            "legacy native scene registry failure coverage"
        ),
        "legacy native scene registry entries": (
            "legacy scene cleanup verifier failure message"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_schema_cache.py": {
        "verify_product_schema_cache": "schema cache privacy coverage",
        "test_product_schema_cache_rejects_raw_device_payloads": (
            "raw payload cache regression coverage"
        ),
        "test_product_schema_cache_allows_schema_text_that_mentions_device": (
            "schema text false-positive coverage"
        ),
        "test_product_schema_cache_rejects_non_object_schema_values": (
            "schema cache object-shape coverage"
        ),
        "product_schema_cache": "schema cache metric coverage",
    },
    "custom_components/yeelight_pro/tests/storage_verifier_helpers.py": {
        "write_storage": "storage verifier fixture writer",
        "config_entry": "storage verifier config entry fixture",
        "yeelight_entities": "storage verifier entity fixture",
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_flow_contracts.py": {
        "test_verify_flow_contracts_accepts_current_runtime_options_boundary": (
            "flow contract verifier success coverage"
        ),
        "test_verify_flow_contracts_rejects_options_flow_without_reload_check": (
            "options reload contract failure coverage"
        ),
        "test_verify_flow_contracts_rejects_config_flow_without_options_factory": (
            "config flow factory failure coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_i18n.py": {
        "test_verify_i18n_contracts_accepts_current_translation_boundary": (
            "i18n verifier success coverage"
        ),
        "test_verify_i18n_contracts_rejects_leaf_key_drift": (
            "translation key drift coverage"
        ),
        "test_verify_i18n_contracts_rejects_missing_required_service_translation": (
            "required service translation coverage"
        ),
        "test_verify_i18n_contracts_rejects_unexpected_translated_service_field": (
            "service field translation contract coverage"
        ),
        "test_verify_i18n_contracts_rejects_untranslated_option_schema_key": (
            "options schema translation coverage"
        ),
        "test_verify_i18n_contracts_rejects_untranslated_selector_option": (
            "selector option translation coverage"
        ),
        "test_verify_i18n_contracts_rejects_scan_login_guidance_drift": (
            "scan-login QR guidance verifier coverage"
        ),
        "test_verify_i18n_contracts_rejects_unknown_repair_placeholder": (
            "unknown Repairs placeholder coverage"
        ),
        "test_verify_i18n_contracts_rejects_untranslated_repair_placeholder": (
            "runtime Repairs placeholder translation coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/i18n_helpers.py": {
        "write_installed_i18n": "i18n verifier installed fixture writer",
        "translation_payload": "i18n verifier translation fixture payload",
        "i18n_service_helpers": "service translation fixture split import",
        "i18n_source_fixture_helpers": "source fixture split import",
        "device_topology_changed": "Repair issue translation fixture key",
    },
    "custom_components/yeelight_pro/tests/i18n_source_fixture_helpers.py": {
        "write_option_schema_sources": "options schema translation fixture source",
        "write_repair_issue_source": "Repair placeholder fixture source",
        "options_schema": "options schema source token",
        "translation_placeholders": "Repair placeholder source token",
        "device_filter_options.py": "device filter selector fixture source",
        "repair_issues.py": "Repair issue fixture source",
    },
    "custom_components/yeelight_pro/tests/i18n_service_helpers.py": {
        "service_yaml_lines": "service yaml fixture source",
        "service_translation_payload": "service translation fixture payload",
        "cleanup_registry": "cleanup service translation fixture coverage",
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_cli.py": {
        "test_build_parser_accepts_repeat_options": "repeat CLI option coverage",
        "test_build_parser_accepts_soak_options": "soak CLI option coverage",
        "test_main_runs_requested_repeat_count": "repeat execution coverage",
        "test_main_fails_when_any_repeat_run_fails": "repeat failure aggregation coverage",
        "test_main_fails_when_repeat_metrics_drift": "repeat drift failure coverage",
        "runtime_entities": "active runtime metric drift coverage",
        "test_main_reports_stable_metrics_when_repeat_metrics_match": (
            "repeat stable metric success coverage"
        ),
        "test_main_runs_soak_until_window_is_covered": (
            "bounded soak execution coverage"
        ),
        "test_main_fails_when_soak_run_fails": "bounded soak failure aggregation",
        "test_run_once_keeps_synthetic_recovery_check_when_docker_is_skipped": (
            "skip-docker synthetic recovery coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_runtime.py": {
        "test_verify_logs_records_recovered_polling_errors_as_fact": (
            "recovered polling error coverage"
        ),
        "test_verify_logs_fails_for_unrecovered_yeelight_errors": (
            "unrecovered runtime error coverage"
        ),
        "test_verify_logs_fails_for_error_after_latest_recovery": (
            "post-recovery error ordering coverage"
        ),
        "test_verify_runtime_entity_counts_accepts_active_distribution": (
            "active runtime entity distribution coverage"
        ),
        "test_verify_runtime_entity_counts_normalizes_spaced_platform_logs": (
            "spaced binary sensor runtime log coverage"
        ),
        "test_verify_runtime_entity_counts_sums_latest_reconcile_per_entry": (
            "multi-entry runtime reconcile total coverage"
        ),
        "test_verify_runtime_entity_counts_rejects_old_switch_leak": (
            "old switch leak runtime failure coverage"
        ),
        "test_verify_runtime_entity_counts_rejects_reconcile_total_mismatch": (
            "active reconcile total mismatch coverage"
        ),
        "test_verify_synthetic_log_recovery_records_contract_fact": (
            "synthetic recovery success coverage"
        ),
        "test_verify_synthetic_log_recovery_fails_on_classifier_drift": (
            "synthetic recovery failure coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_services.py": {
        "test_verify_services_checks_yaml_and_runtime_alignment": (
            "service definition/runtime registration alignment coverage"
        ),
        "test_registered_service_names_resolves_constants_and_literals": (
            "AST service registration parser coverage"
        ),
        "test_registered_service_schema_fields_resolves_imported_constants": (
            "runtime service schema AST coverage"
        ),
        "test_verify_services_fails_for_yaml_field_contract_drift": (
            "services.yaml field contract drift coverage"
        ),
        "test_verify_services_fails_for_runtime_schema_contract_drift": (
            "runtime service schema drift coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_diagnostics.py": {
        "test_verify_diagnostics_capabilities_accepts_release_boundaries": (
            "diagnostics capability verifier success coverage"
        ),
        "test_verify_diagnostics_capabilities_rejects_enabled_live_flag": (
            "disabled live capability verifier coverage"
        ),
        "test_verify_diagnostics_capabilities_rejects_removed_oauth_flag": (
            "removed OAuth flag verifier coverage"
        ),
        "test_verify_diagnostics_capabilities_requires_literal_flags": (
            "literal diagnostics capability parser coverage"
        ),
        "test_verify_diagnostics_capabilities_requires_option_status_fields": (
            "installed option_status field verifier coverage"
        ),
        "test_verify_diagnostics_capabilities_requires_option_status_tokens": (
            "installed option_status token verifier coverage"
        ),
        "scan_interval_seconds": "installed option_status scan-interval field coverage",
        "normalize_entry_options": "installed option_status normalization guard",
    },
    "custom_components/yeelight_pro/tests/local_ha_diagnostics_verifier_helpers.py": {
        "debug_mode_enabled": "installed option_status debug-mode field coverage",
        "CONF_DEVICE_IMPORT_FILTER": "installed option_status filter preview guard",
        "write_websocket_event_runtime": (
            "installed WebSocket event runtime fixture coverage"
        ),
        "include_live_transport_call": (
            "installed WebSocket live-runtime call-edge fixture control"
        ),
        "include_ws_connect_call": (
            "installed WebSocket ws_connect call-edge fixture control"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_websocket_runtime.py": {
        "test_verify_diagnostics_capabilities_requires_websocket_event_runtime": (
            "installed WebSocket event runtime verifier coverage"
        ),
        "test_verify_diagnostics_capabilities_accepts_websocket_event_runtime": (
            "installed WebSocket event runtime success fact coverage"
        ),
        "test_verify_diagnostics_capabilities_requires_websocket_runtime_health": (
            "installed WebSocket runtime health verifier coverage"
        ),
        "test_verify_diagnostics_capabilities_rejects_eventsource_runtime": (
            "installed non-WebSocket event runtime denylist coverage"
        ),
        "test_verify_diagnostics_capabilities_requires_websocket_call_edges": (
            "installed WebSocket runtime call-edge verifier coverage"
        ),
        "WebSocket-only event runtime contract": (
            "installed WebSocket event runtime success fact coverage"
        ),
        "EventSource runtime path": (
            "installed EventSource runtime denial assertion"
        ),
        "*.ws_connect()": "installed WebSocket ws_connect denial assertion",
    },
}
