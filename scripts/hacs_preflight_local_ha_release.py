"""Release-preflight contract tokens for local HA validation."""

from __future__ import annotations

LOCAL_HA_RELEASE_CONTRACT_TOKENS = {
    "scripts/hacs_preflight_local_ha.py": {
        "LOCAL_HA_RELEASE_CONTRACT_TOKENS": "release contract token import",
        "LOCAL_HA_RUNTIME_CONTRACT_TOKENS": "runtime contract token import",
        "VERIFY_LOCAL_HA_CONTRACT_TOKENS": "compatibility token facade",
    },
    "scripts/hacs_preflight_local_ha_release.py": {
        "LOCAL_HA_RELEASE_CONTRACT_TOKENS": "release contract token registry",
        "hacs_preflight_claims.py": "release claim contract coverage",
        "hacs_preflight_core.py": "release core contract coverage",
        "hacs_preflight_release_files.py": "release file registry split coverage",
        "hacs_preflight_runtime_options.py": (
            "runtime options preflight split coverage"
        ),
        "hacs_preflight_split_contracts.py": "split contract coverage",
        "hacs_preflight_lifecycle.py": "lifecycle contract coverage",
        "hacs_preflight_push_contracts.py": "push contract token split coverage",
        "hacs_preflight_local_ha_runtime_sources.py": (
            "runtime source token split coverage"
        ),
        "hacs_preflight_local_ha_runtime_core_tests.py": (
            "runtime core test token split coverage"
        ),
        "hacs_preflight_local_ha_runtime_tests.py": (
            "runtime test token facade coverage"
        ),
        "hacs_preflight_local_ha_runtime_verifier_tests.py": (
            "runtime verifier test token split coverage"
        ),
    },
    "manual_ha_test_helpers.py": {
        "run_named_tests": "manual HA smoke runner helper",
        "print_summary": "manual HA smoke summary helper",
        "sample_light_device": "manual HA smoke device fixture",
    },
    "manual_ha_test_checks.py": {
        "manual_ha_test_core_checks": "manual HA smoke core-check facade import",
        "manual_ha_test_projector_checks": (
            "manual HA smoke projector-check facade import"
        ),
        "manual_ha_test_config_checks": (
            "manual HA smoke config-check facade import"
        ),
        "__all__": "manual HA smoke compatibility export list",
    },
    "manual_ha_test_core_checks.py": {
        "check_integration_import": "manual HA integration import check",
        "check_client_creation": "manual HA client smoke check",
        "check_canonical_models": "manual HA canonical model smoke check",
        "check_config_flow": "manual HA config-flow smoke check",
        "check_platform_entities": "manual HA platform smoke check",
        "check_services": "manual HA service smoke check",
    },
    "manual_ha_test_projector_checks.py": {
        "check_projectors": "manual HA projector smoke check",
        "_check_extra_projectors": "manual HA full projector smoke check",
    },
    "manual_ha_test_config_checks.py": {
        "check_manifest": "manual HA manifest smoke check",
        "check_hacs_json": "manual HA hacs metadata smoke check",
        "check_strings_json": "manual HA strings smoke check",
        "check_config_files": "manual HA config-file smoke check",
    },
    "scripts/preflight_ast.py": {
        "literal_client_capability_flags": "shared diagnostics capability AST parser",
        "_literal_string_dict": "literal dictionary AST parser",
    },
    "scripts/hacs_preflight_claims.py": {
        "STALE_DOC_CLAIMS": "stale literal release claim guard data",
        "STALE_DOC_PATTERNS": "stale regex release claim guard data",
        "OAuth support is implemented": "unverified OAuth claim denylist",
        "live WebSocket updates are implemented": (
            "unverified live WebSocket claim denylist"
        ),
        "analytics runtime is enabled by default": (
            "overstated analytics runtime claim denylist"
        ),
        "house transfer is implemented": "destructive house transfer denylist",
        "device import filter deletes existing entities": (
            "destructive device-filter claim denylist"
        ),
        r"device import filter.{0,40}(?:will|automatically|supports?|implemented).{0,20}": (
            "destructive device-filter regex denylist"
        ),
        r"\d+\s+passed": "fixed pytest count regex denylist",
    },
    "scripts/hacs_preflight_core.py": {
        "MAX_PYTHON_FILE_LINES": "Python source line-count boundary",
        "check_exists": "required file release guard",
        "_gitignore_rules": "required release gitignore guard parser",
        "_is_ignored_by_gitignore": "required release gitignore evaluator",
        "check_json": "metadata JSON release guard",
        "check_platform_constants": "platform constant release guard",
        "check_python_file_line_counts": "Python source line-count release guard",
        "_iter_line_count_python_files": "root Python line-count coverage",
        "RELEASE_QUALITY_GATE_TOKENS": "release quality gate token source",
        "HACS_PUBLISH_REQUIRED_CHECKS": "release script command contract source",
        "check_release_quality_gates": "release quality gate guard",
        "_check_hacs_publish_commands": "release script command guard",
        "check_iot_registry_integrity": "IoT registry integrity release guard",
        "check_readme_claims": "release-facing claim guard",
        "_load_iot_registry_contract": "HA-runtime-free registry loader",
    },
    "scripts/hacs_preflight_release_files.py": {
        "REQUIRED_RELEASE_FILES": "required release file registry",
        "scripts/hacs_preflight_release_files.py": (
            "required release file registry self-guard"
        ),
        "test_config_flow_cloud.py": "config-flow cloud required release file guard",
    },
    "scripts/hacs_preflight_runtime_options.py": {
        "check_automation_contract_tests": "automation contract preflight helper",
        "check_runtime_options_contract_tests": (
            "runtime options contract preflight helper"
        ),
        "async_attach_trigger": "device trigger attach coverage guard",
        "CONF_EXPERIMENTAL_PLATFORMS": (
            "runtime options platform reload token guard"
        ),
        "test_debug_service.py": "debug service runtime-option guard",
        "debug service is gated by debug_mode": "debug service mode gate token",
    },
    "scripts/hacs_preflight_contracts.py": {
        "check_forbidden_open_api_runtime": "dangerous Open API runtime guard",
        "_FORBIDDEN_OPEN_API_RUNTIME_TOKENS": "dangerous Open API token registry",
        "/deliver/": "house transfer endpoint runtime denylist",
        "house_transfer": "house transfer helper runtime denylist",
        "targetUid": "house transfer target user id runtime denylist",
    },
    "scripts/hacs_preflight_push_contracts.py": {
        "PUSH_CONTRACT_REQUIRED_FILES": "push contract token registry",
        "PushReconnectPolicy": "push reconnect policy release guard",
        "tests/test_push_transport.py": "push transport test token guard",
        "tests/test_push_transport_failures.py": (
            "push transport failure test token guard"
        ),
        "tests/test_runtime_bridge_lan_events.py": (
            "runtime bridge LAN event test token guard"
        ),
    },
    "scripts/check_release_zip.py": {
        "FORBIDDEN_PARTS": "release zip forbidden directory guard",
        "FORBIDDEN_SUFFIXES": "release zip generated suffix guard",
        "REQUIRED_FILES": "release zip required runtime file guard",
        "analytics_contract.py": "analytics contract zip required file guard",
        "client_node_api.py": "Open API node helper zip required file guard",
        "client_node_base.py": "Open API node base helper zip required file guard",
        "client_node_lists.py": "Open API node list helper zip required file guard",
        "client_node_properties.py": (
            "Open API node property helper zip required file guard"
        ),
        "config_flow_options.py": "options flow helper zip required file guard",
        "runtime_inference_helpers.py": (
            "runtime inference helper zip required file guard"
        ),
        "oauth_contract.py": "OAuth contract zip required file guard",
        "projector/event_helpers.py": "event projector helper zip required file guard",
        "projector/sensor_helpers.py": "sensor projector helper zip required file guard",
        "name.endswith(\"/\")": "release zip directory entry guard",
        "\"..\" in path.parts": "release zip ZipSlip guard",
        "path.is_absolute()": "release zip absolute path guard",
    },
    "scripts/hacs_preflight_split_contracts.py": {
        "SPLIT_CONTRACT_TEST_TOKENS": "split contract token registry",
        "test_capability_registry_contract.py": "capability split test guard",
        "config_flow_helpers.py": "config-flow helper split test guard",
        "test_config_flow_cloud.py": "config-flow cloud split test guard",
        "test_config_flow_oauth.py": "config-flow OAuth split test guard",
        "test_config_flow_reauth.py": "config-flow reauth split test guard",
        "p0_client_helpers.py": "P0 client helper split test guard",
        "test_p0_client_contracts.py": "P0 client contract split test guard",
        "test_push_payloads.py": "push payload split test guard",
        "config_entry_lifecycle_helpers.py": "config-entry helper split test guard",
        "test_config_entry_unload.py": "config-entry unload split test guard",
        "test_options_flow_contract.py": "options split test guard",
        "test_translation_runtime_contract.py": "translation split test guard",
        "scan-login LOGIN token flow coverage": "scan-login flow coverage reason",
        "shared OAuth client fake coverage": "OAuth fake helper coverage reason",
        "push property payload normalization coverage": (
            "push payload adapter coverage reason"
        ),
        "failed unload runtime preservation coverage": (
            "config-entry unload failure coverage reason"
        ),
        "manual device filter reload coverage": "device filter option coverage reason",
        "Repairs placeholder runtime coverage": "Repair placeholder coverage reason",
    },
    "scripts/hacs_preflight_lifecycle.py": {
        "LIFECYCLE_CONTRACT_TOKENS": "lifecycle contract token registry",
        "async_remove_config_entry_device": "device removal hook guard",
        "cleanup service confirm disable coverage": "explicit cleanup B confirm guard",
        "entry-scoped Repairs cleanup coverage": "Repairs cleanup coverage guard",
        "missing runtime fail-closed coverage": "device removal fail-closed guard",
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_release_quality.py": {
        "test_release_quality_gate_check_requires_lint_and_type_check": (
            "release quality gate drift coverage"
        ),
        "test_release_quality_gate_reports_missing_publish_script": (
            "missing release script coverage"
        ),
        "test_release_quality_gate_rejects_dynamic_publish_checks": (
            "dynamic CHECKS rejection coverage"
        ),
        "local release compile command": "release compile command assertion",
        "hacs_publish.py must define literal CHECKS": (
            "literal publish checks assertion"
        ),
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_release_guards.py": {
        "test_required_release_file_guard_rejects_gitignored_docs": (
            "required release gitignore rejection coverage"
        ),
        "test_required_release_file_guard_allows_unignored_docs": (
            "required release gitignore negation coverage"
        ),
        "test_user_visible_error_redaction_guard_rejects_dynamic_error_text": (
            "user-visible error redaction gate coverage"
        ),
        "test_user_visible_error_redaction_guard_allows_constant_error_text": (
            "user-visible constant error allowance coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_local_ha_guards.py": {
        "test_local_ha_contract_tokens_are_split_by_release_and_runtime": (
            "local HA token facade split coverage"
        ),
        "test_local_ha_verification_contract_requires_safety_tokens": (
            "local HA verification safety token coverage"
        ),
        "_write_local_ha_contract_fixture": (
            "local HA synthetic contract fixture helper"
        ),
        "installed option_status field verifier coverage": (
            "local HA option-status verifier token coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_runtime_options.py": {
        "test_automation_contract_requires_split_device_trigger_tests": (
            "split device-trigger automation guard coverage"
        ),
        "test_runtime_options_contract_requires_debug_service_gate": (
            "debug service runtime-option guard coverage"
        ),
        "matches Yeelight Pro runtime event bus payload": (
            "device trigger runtime bus guard assertion"
        ),
        "device trigger event payload fixture": (
            "device trigger helper guard assertion"
        ),
        "disabled debug-mode service rejection coverage": (
            "debug service disabled-mode guard assertion"
        ),
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_release_claims.py": {
        "test_gap_review_is_scanned_for_stale_release_claims": (
            "ha_xiaomi_home gap review claim guard coverage"
        ),
        "test_all_top_level_docs_are_scanned_for_stale_release_claims": (
            "top-level docs claim scan coverage"
        ),
        "test_release_claim_guard_rejects_new_fixed_test_and_zip_counts": (
            "fixed release metrics claim coverage"
        ),
        "test_release_claim_guard_rejects_house_transfer_claims": (
            "house transfer release claim coverage"
        ),
        "test_release_claim_guard_rejects_overstated_analytics_claims": (
            "overstated analytics release claim coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_device_filter_claims.py": {
        "test_release_claim_guard_rejects_destructive_device_filter_claims": (
            "destructive device-filter release claim coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_protocol_contracts.py": {
        "test_oauth_contract_check_requires_runtime_coverage_tokens": (
            "OAuth protocol preflight coverage"
        ),
        "test_push_contract_check_requires_coverage_tokens": (
            "push protocol preflight coverage"
        ),
        "test_lan_contract_check_requires_coverage_tokens": (
            "LAN protocol preflight coverage"
        ),
        "test_analytics_contract_check_requires_coverage_tokens": (
            "analytics protocol preflight coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_check_release_zip.py": {
        "test_validate_existing_zip_rejects_unsafe_paths": (
            "release zip unsafe path coverage"
        ),
        "test_write_zip_returns_validated_runtime_names": (
            "release zip write/read validation coverage"
        ),
        "unsafe zip path": "unsafe zip path assertion",
        "directory entry is not allowed": "directory entry rejection assertion",
    },
}
