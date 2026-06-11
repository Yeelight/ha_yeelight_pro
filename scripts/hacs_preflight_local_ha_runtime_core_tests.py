"""Runtime core-behavior test contract tokens for local HA validation."""

from __future__ import annotations

LOCAL_HA_RUNTIME_CORE_TEST_TOKENS = {
    "scripts/hacs_preflight_local_ha_runtime_core_tests.py": {
        "LOCAL_HA_RUNTIME_CORE_TEST_TOKENS": "runtime core test token registry",
        "test_entry_migration.py": "entry migration test coverage",
        "test_coordinator_schema_cache_runtime.py": (
            "coordinator schema cache runtime test coverage"
        ),
        "test_refresh_service.py": "refresh service test coverage",
        "test_registry_cleanup_service.py": "registry cleanup service test coverage",
        "test_registry_cleanup_service_privacy.py": (
            "registry cleanup privacy test coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_entry_options_migration.py": {
        "test_normalize_entry_options_clamps_scan_interval": (
            "scan interval migration bounds coverage"
        ),
        "test_normalize_entry_options_canonicalizes_device_import_filter": (
            "nested legacy filter migration coverage"
        ),
        "test_normalize_entry_options_migrates_legacy_device_filter_form_keys": (
            "form-only filter cleanup coverage"
        ),
        "test_normalize_entry_options_disables_filter_without_effective_rules": (
            "empty filter migration coverage"
        ),
        "test_normalize_entry_options_parses_string_bools": (
            "string bool migration coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_entry_migration.py": {
        "test_migrate_cloud_entry_aliases_and_option_defaults": (
            "legacy cloud entry migration coverage"
        ),
        "test_migrate_private_entry_fills_domains_and_default_options": (
            "legacy private entry migration coverage"
        ),
        "test_migrate_current_entry_is_noop": "current entry migration noop coverage",
        "test_normalize_entry_data_preserves_open_api_client_id_alias": (
            "Open API client id alias migration coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_coordinator_topology.py": {
        "test_topology_generation_ignores_state_only_changes": (
            "state-only topology generation coverage"
        ),
        "test_schema_aware_topology_generation_ignores_state_only_changes": (
            "schema-aware state-only topology generation coverage"
        ),
        "test_topology_generation_changes_when_entities_change": (
            "entity topology generation increment coverage"
        ),
        "test_topology_generation_tracks_area_changes": (
            "area topology generation increment coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_coordinator_topology_diff.py": {
        "test_topology_diff_tracks_area_room_membership_changes": (
            "area membership metadata diff coverage"
        ),
        "test_topology_diff_ignores_area_room_membership_order": (
            "stable area membership ordering coverage"
        ),
        "test_topology_diff_classifies_removed_devices": (
            "removed device topology diff coverage"
        ),
        "test_topology_diff_classifies_metadata_changes": (
            "device metadata topology diff coverage"
        ),
        "test_topology_diff_is_empty_for_state_only_changes": (
            "empty state-only topology diff coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_coordinator_schema_cache.py": {
        "test_update_data_attaches_schema_aware_canonical_models": (
            "schema-aware canonical coordinator coverage"
        ),
        "test_runtime_overrides_update_schema_aware_canonical_state": (
            "runtime override canonical state coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_coordinator_schema_cache_runtime.py": {
        "test_product_schema_cache_reuses_schema_between_polls": (
            "schema cache poll reuse coverage"
        ),
        "test_product_schema_manual_refresh_refetches_cached_schema": (
            "manual schema refresh refetch coverage"
        ),
        "test_product_schema_manual_refresh_falls_back_to_cached_schema_on_error": (
            "manual schema refresh fallback coverage"
        ),
        "test_product_schema_cache_reuses_persisted_schema_after_restart": (
            "persisted schema cache restart coverage"
        ),
        "test_product_schema_cache_fetches_only_missing_product_ids": (
            "missing PID schema fetch coverage"
        ),
        "test_product_schema_cache_falls_back_to_cached_schema_on_fetch_error": (
            "poll schema fetch fallback coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/refresh_service_helpers.py": {
        "refresh_entry": "refresh service config entry test helper",
        "refresh_coordinator": "refresh service coordinator test helper",
        "async_request_product_schema_refresh": (
            "refresh service product schema refresh helper coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_refresh_service.py": {
        "test_refresh_service_refreshes_loaded_entries": (
            "manual refresh all entries coverage"
        ),
        "test_refresh_service_rejects_non_admin_user": (
            "manual refresh admin-only coverage"
        ),
        "test_refresh_service_filters_by_entry_id": (
            "manual refresh entry-id filter coverage"
        ),
        "test_refresh_service_rejects_unknown_entry_id_without_echoing_input": (
            "manual refresh entry-id redaction coverage"
        ),
        "test_refresh_service_can_force_product_schema_refresh": (
            "manual refresh product schema refresh coverage"
        ),
        "test_refresh_service_rejects_when_no_valid_entries_refresh": (
            "manual refresh empty-runtime failure coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_refresh_service_post_refresh.py": {
        "test_post_manual_refresh_runs_registry_maintenance": (
            "post-refresh registry maintenance coverage"
        ),
        "test_post_manual_refresh_creates_repair_issue_on_topology_change": (
            "post-refresh topology Repairs coverage"
        ),
        "test_post_manual_refresh_respects_disabled_topology_repairs_option": (
            "post-refresh Repairs option coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_registry_cleanup_service.py": {
        "test_cleanup_registry_service_dry_run_returns_audit_id": (
            "registry cleanup dry-run response coverage"
        ),
        "test_cleanup_registry_service_confirm_disables_stale_entities": (
            "registry cleanup confirm disable coverage"
        ),
        "test_cleanup_registry_service_disables_entities_excluded_by_import_filter": (
            "registry cleanup filtered-device confirm coverage"
        ),
        "test_cleanup_registry_service_rejects_mismatched_audit_id": (
            "registry cleanup audit mismatch coverage"
        ),
        "test_cleanup_registry_service_rejects_missing_user_context": (
            "registry cleanup explicit admin context coverage"
        ),
        "test_cleanup_registry_service_preserves_user_disabled_stale_entity": (
            "registry cleanup user-disabled stale entity preservation coverage"
        ),
        "RegistryEntryDisabler.USER": (
            "registry cleanup real user-disabled marker coverage"
        ),
        "ERROR_ADMIN_CONTEXT_REQUIRED": (
            "registry cleanup missing-admin-context error contract"
        ),
        "removed_entity_ids == []": "registry cleanup no-removal coverage",
    },
    "custom_components/yeelight_pro/tests/test_registry_cleanup_service_privacy.py": {
        "test_cleanup_registry_service_response_and_logs_are_identifier_safe": (
            "registry cleanup response/log privacy coverage"
        ),
        "test_cleanup_registry_service_rejects_stale_audit_after_topology_change": (
            "registry cleanup topology-change replay guard"
        ),
        "secret-device-identifier": "registry cleanup device identifier privacy marker",
        "stale_entities == 2": "registry cleanup changed stale-set assertion",
        "removed_entity_ids == []": "registry cleanup privacy no-removal coverage",
    },
    "custom_components/yeelight_pro/tests/test_entity_lifecycle_reconcile.py": {
        "test_reconcile_treats_filtered_device_entities_as_stale_without_removal": (
            "filtered device stale-without-removal coverage"
        ),
        "registry.updated_entities == []": (
            "filtered device automatic reconcile non-disable coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_entity_lifecycle_reconcile_metadata.py": {
        "test_reconcile_refreshes_active_registry_original_name_and_icon": (
            "active registry metadata refresh coverage"
        ),
        "test_reconcile_does_not_refresh_removed_scene_domain_metadata": (
            "removed scene metadata stale coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_entity_lifecycle_reconcile_entity_id.py": {
        "test_reconcile_renames_legacy_channel_entity_ids": (
            "legacy entity-id migration coverage"
        ),
        "test_reconcile_preserves_user_named_legacy_entity_id": (
            "user-named entity-id preservation coverage"
        ),
        "new_entity_id": "registry entity-id rename assertion",
    },
    "custom_components/yeelight_pro/tests/test_entity_lifecycle_reconcile_display.py": {
        "test_reconcile_marks_extra_double_switch_channel_stale_and_updates_names": (
            "generated switch channel display-name cleanup coverage"
        ),
        "test_reconcile_clears_generated_single_light_original_name": (
            "generated single-light display-name cleanup coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_p0_ha_runtime.py": {
        "test_coordinator_control_device_uses_connected_lan_runtime": (
            "connected LAN device control route coverage"
        ),
        "test_coordinator_control_device_falls_back_to_cloud_when_lan_disconnected": (
            "LAN-disconnected cloud fallback coverage"
        ),
        "test_coordinator_lan_control_error_is_redacted": (
            "LAN control error redaction coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_lan_control_routing.py": {
        "test_coordinator_toggle_device_uses_connected_lan_runtime": (
            "connected LAN device toggle route coverage"
        ),
        "test_coordinator_toggle_device_falls_back_to_cloud_when_lan_disconnected": (
            "LAN-disconnected toggle cloud fallback coverage"
        ),
        "test_coordinator_toggle_device_falls_back_when_lan_health_is_unreadable": (
            "unreadable LAN health cloud fallback coverage"
        ),
        "test_coordinator_lan_toggle_error_is_redacted": (
            "LAN toggle error redaction coverage"
        ),
        "test_coordinator_control_group_uses_connected_lan_for_numeric_group_id": (
            "connected LAN numeric group route coverage"
        ),
        "test_coordinator_control_group_falls_back_to_cloud_for_cloud_group_id": (
            "cloud group-id fallback coverage"
        ),
        "test_coordinator_execute_scene_uses_connected_lan_for_numeric_scene_id": (
            "connected LAN numeric scene route coverage"
        ),
        "test_coordinator_execute_scene_falls_back_to_cloud_for_cloud_scene_id": (
            "cloud scene-id fallback coverage"
        ),
        "test_coordinator_lan_scene_error_is_redacted": (
            "LAN scene error redaction coverage"
        ),
        "test_coordinator_lan_group_control_error_is_redacted": (
            "LAN group error redaction coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_schema_cache.py": {
        "test_cache_storage_data_drops_sensitive_runtime_context": (
            "schema cache source privacy coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_schema_cache_logging.py": {
        "test_cache_force_refresh_failure_log_is_aggregate_only": (
            "schema cache force-refresh log redaction coverage"
        ),
        "test_cache_load_error_log_does_not_expose_sensitive_details": (
            "schema cache load log redaction coverage"
        ),
        "test_cache_fetch_error_log_does_not_expose_sensitive_details": (
            "schema cache fetch log redaction coverage"
        ),
    },
}
