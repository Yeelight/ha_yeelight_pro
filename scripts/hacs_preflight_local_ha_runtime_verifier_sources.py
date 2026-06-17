"""Local HA verifier source contract tokens for local HA validation."""

from __future__ import annotations

from scripts.hacs_preflight_local_ha_runtime_verifier_storage import (
    LOCAL_HA_RUNTIME_VERIFIER_STORAGE_TOKENS,
)

LOCAL_HA_RUNTIME_VERIFIER_SOURCE_TOKENS = {
    "scripts/hacs_preflight_local_ha_runtime_verifier_sources.py": {
        "LOCAL_HA_RUNTIME_VERIFIER_SOURCE_TOKENS": (
            "runtime verifier source token registry"
        ),
        "LOCAL_HA_RUNTIME_VERIFIER_STORAGE_TOKENS": (
            "storage verifier source token registry import"
        ),
        "scripts/verify_local_ha.py": "verify-local-ha source token coverage",
        "scripts/local_ha_verification/diagnostics.py": (
            "diagnostics verifier source token coverage"
        ),
        "scripts/local_ha_verification/diagnostics_websocket.py": (
            "diagnostics WebSocket verifier source token coverage"
        ),
        "scripts/local_ha_verification/runtime_entities.py": (
            "runtime entity verifier source token coverage"
        ),
    },
    "scripts/verify_local_ha.py": {
        "scripts.local_ha_verification.cli": "thin compatibility CLI facade",
        "verify_diagnostics_capabilities": "diagnostics capability verifier export",
        "scripts.local_ha_verification.storage": "storage privacy helper exports",
        "scripts.local_ha_verification.options": "option verifier exports",
        "REQUIRED_OPTIONS_FLOW_TOKENS": "flow contract verifier export",
        "verify_flow_contracts": "flow contract verifier export",
        "REQUIRED_I18N_LEAF_PATHS": "i18n required path contract export",
        "verify_i18n_contracts": "i18n verifier export",
        "installed_enabled_platforms": "platform/options verifier export",
        "SERVICE_FIELD_CONTRACTS": "service field contract export",
        "registered_service_schema_fields": "runtime service schema export",
        "registered_service_names": "runtime service registration export",
        "verify_required_modules": "installed support module presence export",
        "verify_product_schema_cache": "product schema privacy scan export",
        "verify_synthetic_log_recovery": "synthetic runtime recovery verifier export",
        "verify_runtime_entity_counts": "active runtime entity verifier export",
        "latest_reconciled_active_total": "multi-entry active reconcile total export",
    },
    "scripts/verify_local_ha_soak.py": {
        "scripts.local_ha_verification.cli": "dedicated soak uses shared CLI",
        "DEFAULT_SOAK_SECONDS": "dedicated soak default window token",
        "DEFAULT_SOAK_INTERVAL": "dedicated soak default interval token",
        "build_soak_argv": "dedicated soak argv builder token",
        "verify_local_ha_main": "dedicated soak shared verifier token",
    },
    "scripts/verify_local_ha_recovery.py": {
        "scripts.local_ha_verification.cli": "dedicated recovery uses shared CLI",
        "DEFAULT_RECOVERY_REPEAT": "dedicated recovery repeat default token",
        "DEFAULT_RECOVERY_LOG_TAIL": "dedicated recovery log-tail default token",
        "build_recovery_argv": "dedicated recovery argv builder token",
        "recovery verification requires Docker log access": (
            "dedicated recovery Docker log guard token"
        ),
        "verify_local_ha_main": "dedicated recovery shared verifier token",
    },
    "scripts/sync_local_ha_runtime.py": {
        "sync_runtime_files": "local HA runtime sync helper",
        "EXCLUDED_COMPARE_PARTS": "runtime sync excludes tests and caches",
        "EXCLUDED_COMPARE_SUFFIXES": "runtime sync excludes bytecode suffixes",
        "FORBIDDEN_INSTALL_NAMES": "runtime sync excludes forbidden install files",
        "forbidden_install_paths": "post-sync install hygiene guard",
        "forbidden local HA install files remain": "post-sync failure message",
    },
    "scripts/local_ha_verification/diagnostics.py": {
        "DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES": (
            "disabled live capability verifier contract"
        ),
        "DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES": (
            "enabled contract capability verifier contract"
        ),
        "DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES": (
            "forbidden ambiguous capability verifier contract"
        ),
        "verify_diagnostics_capabilities": "installed diagnostics capability check",
        "diagnostics_capabilities": "diagnostics metric stability key",
        "REQUIRED_OPTION_STATUS_FIELDS": "installed option_status field contract",
        "REQUIRED_OPTION_STATUS_TOKENS": "installed option_status token contract",
        "_verify_option_status_contract": "installed option_status verifier",
        "_literal_option_status_fields": "installed option_status AST parser",
        "debug_mode_enabled": "installed option_status debug-mode guard",
        "scan_interval_seconds": "installed option_status scan-interval guard",
        "diagnostics_option_status": "option_status metric stability key",
        "REQUIRED_DIAGNOSTIC_PAYLOAD_REDACTION_TOKENS": (
            "installed diagnostic payload redaction token contract"
        ),
        "_verify_diagnostic_payload_redaction_contract": (
            "installed diagnostic payload redaction verifier"
        ),
        "_literal_redaction_names": (
            "installed diagnostic payload redaction AST parser"
        ),
        "CONF_SCAN_LOGIN_DEVICE": "scan-login device redaction guard",
        "diagnostics_payload_redaction": (
            "diagnostic payload redaction metric stability key"
        ),
        "verify_websocket_event_runtime_contract": (
            "installed WebSocket-only event runtime verifier call"
        ),
    },
    "scripts/local_ha_verification/diagnostics_websocket.py": {
        "REQUIRED_WEBSOCKET_EVENT_RUNTIME_TOKENS": (
            "installed WebSocket event runtime required-token contract"
        ),
        "FORBIDDEN_WEBSOCKET_EVENT_RUNTIME_TOKENS": (
            "installed non-WebSocket event runtime denylist"
        ),
        "verify_websocket_event_runtime_contract": (
            "installed WebSocket-only event runtime verifier"
        ),
        "_missing_websocket_runtime_call_edges": (
            "installed WebSocket runtime call-edge verifier"
        ),
        "_ast_has_attribute_call": (
            "installed WebSocket ws_connect AST guard"
        ),
        "missing_call_edges": (
            "WebSocket event runtime call-edge metric key"
        ),
        "PUSH_DATA_TYPES": (
            "installed shared prop/event push frame contract guard"
        ),
        "PUSH_CONTROL_METHODS": (
            "installed shared subscribe/heartbeat control frame contract guard"
        ),
        "last_runtime_error_type": (
            "installed WebSocket runtime error health guard"
        ),
        "last_handshake_status": (
            "installed WebSocket handshake status health guard"
        ),
        "last_disconnect_reason": (
            "installed WebSocket disconnect reason health guard"
        ),
        "_sync_transport_runtime_error": (
            "installed PushManager transport error health sync guard"
        ),
        "WebSocket-only event runtime contract present": (
            "installed WebSocket-only event runtime success fact"
        ),
        "websocket_event_runtime": "WebSocket event runtime metric key",
    },
    "scripts/local_ha_verification/install.py": {
        "runtime_diff": "source/install runtime drift check",
        "forbidden_install_paths": "release-excluded install artifact check",
        "verify_required_modules": "installed support module presence check",
        "verify_installation": "installed component shape check",
    },
    "scripts/local_ha_verification/flow_contracts.py": {
        "REQUIRED_OPTIONS_FLOW_TOKENS": "options flow required token contract",
        "REQUIRED_OPTIONS_FLOW_STEPS": "options flow confirmation step contract",
        "verify_flow_contracts": "installed flow contract verifier",
        "_create_entry_uses_pending_options": "pending options persistence AST guard",
        "_returns_options_flow": "config flow options factory AST guard",
        "flow_contracts": "flow contract stability metric",
    },
    "scripts/local_ha_verification/i18n.py": {
        "TRANSLATION_FILES": "installed translation file contract",
        "REQUIRED_I18N_LEAF_PATHS": "required translation key path contract",
        "verify_i18n_contracts": "installed i18n verifier",
        "_verify_leaf_paths": "translation key alignment guard",
        "_verify_service_translations": "service translation contract guard",
        "_verify_repair_placeholders": "Repair issue placeholder alignment guard",
        "_verify_scan_login_translation_guidance": "scan-login QR guidance guard",
        "SCAN_LOGIN_PLACEHOLDERS": "scan-login QR placeholder contract",
        "remaining_seconds": "scan-login countdown placeholder guard",
        "poll_count": "scan-login polling count placeholder guard",
        "Yeelight APP 1.5.0": "scan-login APP version guidance guard",
        "read_translation_payloads": "translation payload reader integration",
        "installed_option_translation_keys": "options schema translation parser integration",
        "installed_selector_option_translation_paths": (
            "selector option translation parser integration"
        ),
        "installed_repair_placeholder_keys": (
            "Repair issue runtime placeholder parser integration"
        ),
        "i18n_translations": "i18n stability metric",
    },
    "scripts/local_ha_verification/i18n_payloads.py": {
        "read_translation_payloads": "installed translation payload reader",
        "json.JSONDecodeError": "invalid translation JSON failure guard",
        "leaf_paths": "translation leaf path helper",
        "mapping_at": "nested translation mapping helper",
        "value_at": "nested translation value helper",
        "format_paths": "translation key path failure formatting",
    },
    "scripts/local_ha_verification/i18n_source.py": {
        "installed_option_translation_keys": "installed options schema parser",
        "installed_selector_option_translation_paths": (
            "installed selector option translation parser"
        ),
        "_LEGACY_STORAGE_OPTION_KEYS": (
            "legacy storage option keys excluded from visible i18n requirements"
        ),
        "SelectSelectorConfig": "selector translation source parser",
        "installed_repair_placeholder_keys": "Repair issue placeholder parser",
        "_schema_key_value": "vol schema translation key resolver",
        "_dict_keys_from_comprehension": "Repair dict comprehension parser",
        "async_create_issue": "Repair issue source call target",
        "translation_placeholders": "Repair placeholder source keyword",
    },
    "scripts/local_ha_verification/options.py": {
        "verify_config_entry_options": "config entry option status check",
        "REQUIRED_CONFIG_ENTRY_OPTION_KEYS": "config entry required option keys",
        "OPTIONAL_CONFIG_ENTRY_OPTION_KEYS": "config entry optional option keys",
        "_expected_option_defaults": "option defaults constant parser",
        "_invalid_option_values": "option bounds validation",
        "_enabled_device_filter_count": "device filter aggregate status",
        "config_entry_options": "option stability metric",
    },
    "scripts/local_ha_verification/platforms.py": {
        "verify_platform_options_alignment": "installed platform/options alignment check",
        "installed_enabled_platforms": "installed enabled platform helper",
        "_installed_platform_contract": "literal platform constants parser",
        "_literal_module_lists": "literal string-list AST parser",
        "entity domains are not enabled by config entry options": (
            "unsupported platform runtime guard"
        ),
        "platform_options": "platform/options stability metric",
    },
    "scripts/local_ha_verification/services.py": {
        "REQUIRED_SERVICES": "service definition verification",
        "registered_service_names": "runtime service registration scan",
        "_service_name_from_call": "AST service registration parser",
        "verify_service_schema_contracts": "service field schema verifier call",
        "verify_services": "installed service definition check",
        "services": "service registration stability metric",
    },
    "scripts/local_ha_verification/service_schema.py": {
        "SERVICE_FIELD_CONTRACTS": "service field release contract",
        "documented_service_field_contracts": "services.yaml field parser",
        "registered_service_schema_fields": "runtime service schema parser",
        "_registered_service_schema_fields": "runtime service schema parser facade",
        "verify_service_schema_contracts": "service field schema verifier",
        "service_field_schemas": "service field stability metric",
    },
    "scripts/local_ha_verification/service_schema_runtime.py": {
        "registered_service_schema_fields": "runtime service schema AST helper",
        "_field_contract_from_schema_key": "AST vol.Schema field parser",
        "_service_schema_from_call": "AST service schema registration parser",
        "_all_string_constants": "cross-module string constant scanner",
        "_schema_fields_by_name": "vol.Schema assignment scanner",
        "_schema_keyword_name": "service schema keyword scanner",
    },
    "scripts/local_ha_verification/runtime.py": {
        "verify_logs": "Yeelight Pro log failure scan",
        "verify_runtime_entities": "active runtime entity verification orchestration",
        "verify_runtime_entity_counts": "runtime entity count helper call",
        "verify_synthetic_log_recovery": "synthetic recovery classification check",
        "synthetic_runtime_recovery": "synthetic recovery stability metric",
        "bad_line_entries": "indexed runtime log error scan",
        "recovery_index > index": "time-ordered recovery validation",
        "verify_docker": "local Docker health check",
        "verify_ha_url": "local HA reachability check",
    },
    "scripts/local_ha_verification/runtime_entities.py": {
        "ADDED_ENTITIES_RE": "English active platform add log parser",
        "ZH_ADDED_ENTITIES_RE": "Chinese active platform add log parser",
        "RECONCILED_ACTIVE_RE": "entity registry reconcile active parser",
        "_normalize_domain": "spaced platform log domain normalizer",
        "verify_runtime_entity_counts": "active runtime entity distribution verifier",
        "runtime_entity_counts": "active platform count aggregator",
        "latest_reconciled_active_count": "latest active reconcile count helper",
        "latest_reconciled_active_total": "multi-entry active reconcile total helper",
        "runtime_entity_domains": "active runtime domain stability metric",
        "runtime active entity total mismatch": "active/reconcile mismatch guard",
    },
    "scripts/local_ha_verification/constants.py": {
        "BAD_LOG_MARKERS": "runtime error marker denylist",
        "REQUIRED_RUNTIME_MODULES": "installed support module presence list",
        "config_flow_precheck": "config-flow network precheck helper presence check",
        "scan_login_contract": "scan-login no-network module presence check",
        "config_flow_reauth": "scan-login reauth config flow helper presence check",
        "config_flow_scan_login": "scan-login config flow helper presence check",
        "core.lan_control": "LAN local control helper presence check",
        "core.coordinator_controls": "coordinator LAN-first control helper check",
        "push_contract": "push contract module presence check",
        "push_manager": "push manager module presence check",
        "push_transport": "experimental push transport module presence check",
        "entity_lifecycle_cleanup": "registry cleanup helper module presence check",
        "entity_lifecycle_entity_id": "entity id migration helper module presence check",
        "registry_cleanup_service": "cleanup registry service module presence check",
        "entity_candidate_logging": "entity candidate logging module presence check",
        "capabilities.spec_correction_normalizers": (
            "spec correction normalizer runtime module presence check"
        ),
        "converter.runtime_inference_helpers": (
            "runtime inference helper module presence check"
        ),
        "converter.runtime_registry_events": (
            "runtime registry event helper module presence check"
        ),
        "converter.openapi_properties": (
            "OpenAPI property helper module presence check"
        ),
        "converter.runtime_template_controls": (
            "runtime control template module presence check"
        ),
        "converter.runtime_template_sensors": (
            "runtime sensor template module presence check"
        ),
        "converter.runtime_template_hvac": (
            "runtime HVAC template module presence check"
        ),
        "converter.runtime_templates": (
            "runtime template facade module presence check"
        ),
        "converter.runtime_subdevices": (
            "OpenAPI sub-device helper module presence check"
        ),
        "core.device_registry_classification": (
            "registry-backed classification helper module presence check"
        ),
        "core.device_runtime_constants": (
            "runtime capability constants module presence check"
        ),
        "lan_contract": "LAN contract module presence check",
        "lan_methods": "LAN method constants module presence check",
        "lan_payload": "LAN payload adapter module presence check",
        "core.client_node_base": "node API base helper runtime module presence check",
        "core.client_node_api": "node API helper runtime module presence check",
        "core.client_node_lists": "node API list helper runtime module presence check",
        "core.client_node_properties": (
            "node API property helper runtime module presence check"
        ),
        "core.client_request": "request helper runtime module presence check",
        "core.coordinator_runtime": "coordinator runtime helper presence check",
        "core.runtime_bridge": "runtime bridge helper presence check",
        "device_trigger": "device automation trigger module presence check",
        "projector.event_identity_helpers": (
            "event identity helper runtime module presence check"
        ),
        "projector.event_helpers": "event projector helper runtime module presence check",
        "projector.sensor_helpers": "sensor projector helper runtime module presence check",
        "ha_device_registry": "HA device registry sync module presence check",
        "ha_house_registry": "HA house helper registry module presence check",
        "SENSITIVE_CACHE_MARKERS": "sensitive marker denylist",
        "SENSITIVE_CACHE_VALUE_PATTERNS": "sensitive value pattern denylist",
    },
    "scripts/local_ha_verification/cli.py": {
        "build_parser": "CLI parser",
        "parse_domain_counts": "expected count parser",
        "--repeat": "bounded repeat validation option",
        "--repeat-delay": "bounded repeat delay option",
        "--soak-seconds": "bounded soak validation option",
        "--soak-interval": "bounded soak interval option",
        "_run_soak": "time-window verification orchestration",
        "_verify_stable_metrics": "multi-run metric drift gate",
        "stable metric drift": "multi-run drift failure message",
        "time.monotonic": "bounded soak monotonic clock",
        "_run_once": "single-run verification orchestration",
        "DRIFT_EXCLUDED_METRICS": "retained registry drift exclusion contract",
        "verify_flow_contracts": "flow contract check orchestration",
        "verify_i18n_contracts": "i18n contract check orchestration",
        "verify_diagnostics_capabilities": "diagnostics check orchestration",
        "verify_installation": "install check orchestration",
        "verify_storage": "storage check orchestration",
        "verify_runtime_entities": "active runtime entity check orchestration",
        "verify_synthetic_log_recovery": "synthetic recovery check orchestration",
    },
}

LOCAL_HA_RUNTIME_VERIFIER_SOURCE_TOKENS.update(
    LOCAL_HA_RUNTIME_VERIFIER_STORAGE_TOKENS
)
