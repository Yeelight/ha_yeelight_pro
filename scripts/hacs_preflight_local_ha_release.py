"""Release-preflight contract tokens for local HA validation."""

from __future__ import annotations

from scripts.hacs_preflight_legacy_entrypoints import (
    LEGACY_LOCAL_HA_ENTRYPOINT_TOKENS,
)
from scripts.hacs_preflight_local_ha_split_contracts import (
    LOCAL_HA_SPLIT_CONTRACT_TOKENS,
)
from scripts.hacs_preflight_local_ha_probes import (
    LOCAL_HA_PRODUCTION_PROBE_TOKENS,
)
from scripts.hacs_preflight_local_ha_protocol_contracts import (
    LOCAL_HA_PROTOCOL_CONTRACT_TOKENS,
)
from scripts.hacs_preflight_manual_tests import MANUAL_HA_TEST_TOKENS

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
        "hacs_preflight_legacy_entrypoints.py": (
            "legacy entrypoint token split coverage"
        ),
        "hacs_preflight_manual_tests.py": (
            "manual HA smoke token split coverage"
        ),
        "hacs_preflight_runtime_options.py": (
            "runtime options preflight split coverage"
        ),
        "hacs_preflight_local_ha_split_contracts.py": (
            "split-contract release token split coverage"
        ),
        "hacs_preflight_split_contracts.py": "split contract coverage",
        "hacs_preflight_lifecycle.py": "lifecycle contract coverage",
        "hacs_preflight_local_ha_protocol_contracts.py": (
            "protocol contract token split coverage"
        ),
        "hacs_preflight_local_ha_probes.py": (
            "production probe token split coverage"
        ),
        "scripts/verify_local_ha_recovery.py": (
            "dedicated local HA recovery script token guard"
        ),
        "custom_components/yeelight_pro/tests/test_verify_local_ha_recovery.py": (
            "dedicated local HA recovery test token guard"
        ),
        "scripts/verify_local_ha_soak.py": (
            "dedicated local HA soak script token guard"
        ),
        "custom_components/yeelight_pro/tests/test_verify_local_ha_soak.py": (
            "dedicated local HA soak test token guard"
        ),
        "hacs_preflight_local_ha_runtime_sources.py": (
            "runtime source token split coverage"
        ),
        "hacs_preflight_local_ha_runtime_verifier_sources.py": (
            "runtime verifier source token split coverage"
        ),
        "hacs_preflight_local_ha_runtime_verifier_storage.py": (
            "runtime verifier storage token split coverage"
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
        "FORBIDDEN_RUNTIME_PLATFORM_FILES": "unsupported runtime platform denylist",
        "check_forbidden_runtime_platform_files": (
            "unsupported runtime platform file guard"
        ),
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
        "hacs_preflight_local_ha_protocol_contracts.py": (
            "protocol token registry required release file guard"
        ),
        "test_config_flow_cloud.py": "config-flow cloud required release file guard",
        "test_config_flow_cloud_devices.py": (
            "config-flow cloud device picker required release file guard"
        ),
        "test_config_flow_entry_creation.py": (
            "config-flow entry creation required release file guard"
        ),
    },
    "scripts/hacs_preflight_runtime_options.py": {
        "check_automation_contract_tests": "automation contract preflight helper",
        "check_runtime_options_contract_tests": (
            "runtime options contract preflight helper"
        ),
        "async_attach_trigger": "device trigger attach coverage guard",
        "CONF_HIDE_UNKNOWN_ENTITIES": "runtime options reload token guard",
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
    "scripts/check_release_zip.py": {
        "FORBIDDEN_PARTS": "release zip forbidden directory guard",
        "FORBIDDEN_SUFFIXES": "release zip generated suffix guard",
        "REQUIRED_FILES": "release zip required runtime file guard",
        "entity_category.py": "entity category helper zip required file guard",
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
        "runtime_template_controls.py": (
            "runtime control template zip required file guard"
        ),
        "runtime_template_sensors.py": (
            "runtime sensor template zip required file guard"
        ),
        "runtime_template_hvac.py": (
            "runtime HVAC template zip required file guard"
        ),
        "runtime_templates.py": "runtime template facade zip required file guard",
        "runtime_subdevices.py": "OpenAPI sub-device helper zip required file guard",
        "scan_login_contract.py": "scan-login contract zip required file guard",
        "projector/event_helpers.py": "event projector helper zip required file guard",
        "projector/property_control_common.py": (
            "property control common helper zip required file guard"
        ),
        "projector/sensor_helpers.py": "sensor projector helper zip required file guard",
        "name.endswith(\"/\")": "release zip directory entry guard",
        "\"..\" in path.parts": "release zip ZipSlip guard",
        "path.is_absolute()": "release zip absolute path guard",
    },
    "scripts/verify_local_ha_recovery.py": {
        "DEFAULT_RECOVERY_REPEAT": "dedicated local HA recovery repeat default",
        "DEFAULT_RECOVERY_LOG_TAIL": "dedicated local HA recovery log-tail default",
        "build_recovery_argv": "dedicated local HA recovery argv builder",
        "recovery verification requires Docker log access": (
            "dedicated local HA recovery docker-log guard"
        ),
        "verify_local_ha_main": "dedicated local HA recovery shared verifier reuse",
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_recovery.py": {
        "test_build_recovery_argv_adds_repeat_and_log_tail_defaults": (
            "dedicated local HA recovery default coverage"
        ),
        "test_build_recovery_argv_rejects_skip_docker": (
            "dedicated local HA recovery docker-log guard coverage"
        ),
        "test_recovery_main_delegates_to_shared_verifier": (
            "dedicated local HA recovery verifier reuse coverage"
        ),
        "test_script_help_path_execution_imports_cleanly": (
            "dedicated local HA recovery script path coverage"
        ),
    },
    "scripts/verify_local_ha_soak.py": {
        "DEFAULT_SOAK_SECONDS": "dedicated local HA soak default window",
        "DEFAULT_SOAK_INTERVAL": "dedicated local HA soak interval",
        "build_soak_argv": "dedicated local HA soak argv builder",
        "verify_local_ha_main": "dedicated local HA soak shared verifier reuse",
    },
    "custom_components/yeelight_pro/tests/test_verify_local_ha_soak.py": {
        "test_build_soak_argv_adds_bounded_defaults": (
            "dedicated local HA soak default coverage"
        ),
        "test_soak_main_delegates_to_shared_verifier": (
            "dedicated local HA soak verifier reuse coverage"
        ),
        "test_script_help_path_execution_imports_cleanly": (
            "dedicated local HA soak script path coverage"
        ),
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
        "hacs_preflight_local_ha_helpers": (
            "local HA synthetic fixture helper import"
        ),
        "installed option_status field verifier coverage": (
            "local HA option-status verifier token coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/hacs_preflight_local_ha_helpers.py": {
        "_write_local_ha_contract_fixture": (
            "local HA synthetic contract fixture helper"
        ),
        "hacs_preflight_local_ha_runtime_verifier_tests.py": (
            "local HA synthetic fixture release/runtime token"
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
        "test_top_level_goal_audit_is_scanned_for_stale_release_claims": (
            "goal audit claim guard coverage"
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
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_release_claims_picker.py": {
        "test_release_claim_guard_rejects_setup_only_device_picker_claims": (
            "setup-only device picker claim coverage"
        ),
        "options cannot reopen the device picker": (
            "options device picker rollback claim sample"
        ),
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_device_filter_claims.py": {
        "test_release_claim_guard_rejects_destructive_device_filter_claims": (
            "destructive device-filter release claim coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_hacs_preflight_protocol_contracts.py": {
        "test_scan_login_contract_check_requires_runtime_coverage_tokens": (
            "scan-login protocol preflight coverage"
        ),
        "test_push_contract_check_requires_coverage_tokens": (
            "push protocol preflight coverage"
        ),
        "test_lan_contract_check_requires_coverage_tokens": (
            "LAN protocol preflight coverage"
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

LOCAL_HA_RELEASE_CONTRACT_TOKENS.update(LEGACY_LOCAL_HA_ENTRYPOINT_TOKENS)
LOCAL_HA_RELEASE_CONTRACT_TOKENS.update(LOCAL_HA_SPLIT_CONTRACT_TOKENS)
LOCAL_HA_RELEASE_CONTRACT_TOKENS.update(LOCAL_HA_PRODUCTION_PROBE_TOKENS)
LOCAL_HA_RELEASE_CONTRACT_TOKENS.update(LOCAL_HA_PROTOCOL_CONTRACT_TOKENS)
LOCAL_HA_RELEASE_CONTRACT_TOKENS.update(MANUAL_HA_TEST_TOKENS)
