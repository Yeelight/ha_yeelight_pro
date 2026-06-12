"""Lifecycle release preflight checks for Yeelight Pro."""

from __future__ import annotations

from pathlib import Path

LIFECYCLE_CONTRACT_TOKENS = {
    "__init__.py": {
        "async_remove_config_entry_device": "HA device removal hook",
        "async_register_registry_cleanup_service": "explicit cleanup service registration",
        "_async_stop_loaded_runtime": "config-entry runtime stop helper",
        "get(entry.entry_id)": "runtime lookup before stop cleanup",
        "pop(entry.entry_id": "runtime removal after stop cleanup",
        "push_manager": "optional push manager unload cleanup",
        "_async_sync_gateway_devices": "compatibility device sync import",
        "_active_device_identifiers": "compatibility active identifier import",
        "_device_payload_identifiers": "compatibility payload identifier import",
    },
    "ha_device_registry.py": {
        "async_sync_gateway_devices": "gateway/source device registry sync",
        "active_device_identifiers": "active device identifier guard",
        "device_payload_identifiers": "payload identifier extraction guard",
        "sync_house_device": "house helper registry sync integration",
    },
    "ha_house_registry.py": {
        "sync_house_device": "house helper registry sync facade",
        "_house_device_entries": "legacy house helper registry matcher",
        "_safe_house_identifiers": "duplicate house helper identifier guard",
        "is_house_placeholder_name": "house placeholder user-name cleanup guard",
    },
    "entity_lifecycle.py": {
        "async_reconcile_entity_registry": "entity registry reconcile hook",
        "entity_lifecycle_cleanup": "cleanup helper facade imports",
        "entity_lifecycle_entity_id": "safe entity-id helper facade import",
        "_registry_entry_disabled_by_user": "user-disabled entity preservation",
        "_restore_active_integration_entries": "active integration-disabled entity restoration",
        "EntityRegistryReconcileSummary": "aggregate diagnostics summary",
        "collect_entity_candidate_keys": "filtered candidate lifecycle source",
    },
    "entity_lifecycle_entity_id.py": {
        "safe_entity_id_migration": "safe legacy entity-id migration helper",
        "registry_entity_ids": "entity-id conflict set helper",
        "_legacy_unique_id_tail": "legacy channel suffix detector",
        "_registry_entry_disabled_by_user": "user-disabled rename preservation",
    },
    "entity_candidates.py": {
        "CONF_DEVICE_IMPORT_FILTER": "candidate-level device import filter lookup",
        "matches_device_import_filter": "candidate-level device import filter match",
    },
    "entity_lifecycle_cleanup.py": {
        "async_preview_stale_registry_cleanup": "cleanup dry-run helper",
        "async_disable_stale_registry_entities": "confirmed cleanup disable helper",
        "EntityRegistryCleanupAudit": "cleanup audit diagnostics summary",
        "_cleanup_audit_id": "dry-run audit id contract",
    },
    "registry_cleanup_service.py": {
        "SERVICE_CLEANUP_REGISTRY": "cleanup registry service name",
        "supports_response=SupportsResponse.OPTIONAL": "cleanup service returns dry-run audit",
        "ERROR_CONFIRM_REQUIRES_AUDIT": "confirm requires audit id",
        "ERROR_AUDIT_MISMATCH": "mismatched dry-run rejection",
        "async_disable_stale_registry_entities": "service uses lifecycle cleanup helper",
    },
    "repair_issues.py": {
        "async_create_topology_changed_issue": "topology Repairs issue creation",
        "async_delete_topology_changed_issues": "entry removal Repairs cleanup",
        "_topology_diff_summary": "topology diff sanitizer",
        "_TOPOLOGY_DIFF_COUNT_KEYS": "aggregate-only Repairs count allowlist",
        "sha256": "redacted Repairs issue entry scope",
        "_topology_issue_entry_scope": "hashed Repairs issue entry scope helper",
        "_legacy_topology_issue_id": "legacy raw Repairs issue cleanup helper",
    },
    "tests/test_device_removal.py": {
        "test_remove_config_entry_device_rejects_active_source_device": (
            "active source device removal rejection coverage"
        ),
        "test_remove_config_entry_device_rejects_active_gateway_device": (
            "active gateway device removal rejection coverage"
        ),
        "test_remove_config_entry_device_allows_stale_yeelight_device": (
            "stale device removal coverage"
        ),
        "test_remove_config_entry_device_rejects_when_runtime_missing": (
            "missing runtime fail-closed coverage"
        ),
    },
    "tests/test_ha_device_registry.py": {
        "test_sync_gateway_devices_updates_legacy_house_placeholder_devices": (
            "legacy house helper placeholder migration coverage"
        ),
        "House 12345": "legacy house placeholder fixture",
        "Yeelight Pro 家庭": "friendly house helper model assertion",
    },
    "tests/ha_device_registry_helpers.py": {
        "DeviceRegistryCoordinator": "shared HA device registry coordinator helper",
        "fallback_device_payload": "shared fallback metadata-only device fixture",
        "device_payload": "shared canonical device registry fixture",
    },
    "tests/test_ha_device_registry_metadata.py": {
        "test_sync_gateway_devices_normalizes_canonical_generic_model": (
            "canonical generic model metadata cleanup coverage"
        ),
        "test_sync_gateway_devices_replaces_generic_model_label_without_model_id": (
            "legacy generic model metadata cleanup coverage"
        ),
        "relay_switch": "generic model fixture",
        "双键开关": "friendly switch model assertion",
    },
    "tests/entity_lifecycle_helpers.py": {
        "FakeEntityRegistry": "shared lifecycle registry fake",
        "patch_entity_registry": "shared lifecycle registry patch helper",
        "reconcile_diagnostics": "shared lifecycle diagnostics helper",
        '"pending_stale": pending_stale': "stale entity pending diagnostics helper",
    },
    "tests/registry_cleanup_service_helpers.py": {
        "install_cleanup_runtime": "cleanup service runtime test helper",
        "patch_device_registry": "cleanup service device registry patch helper",
        "admin_context": "cleanup service admin-context helper",
        "call_cleanup_registry": "cleanup service call helper",
    },
    "tests/test_entity_lifecycle_reconcile.py": {
        "test_reconcile_marks_stale_registry_entry_pending_without_removal": (
            "first-pass stale entity pending coverage"
        ),
        "test_reconcile_keeps_same_stale_registry_entry_on_second_pass": (
            "automatic stale entity non-deletion coverage"
        ),
        "test_reconcile_preserves_user_disabled_stale_registry_entry": (
            "user-disabled entity preservation coverage"
        ),
        "test_reconcile_clears_pending_when_stale_registry_entry_is_active_again": (
            "active-again stale pending reset coverage"
        ),
        "test_reconcile_preserves_active_user_disabled_entry": (
            "active user-disabled entity preservation coverage"
        ),
        "test_reconcile_marks_removed_scene_domain_stale_when_button_is_active": (
            "removed scene platform stale coverage"
        ),
        "test_reconcile_treats_filtered_device_entities_as_stale_without_removal": (
            "filtered device stale-without-removal coverage"
        ),
    },
    "tests/test_entity_lifecycle_reconcile_metadata.py": {
        "test_reconcile_refreshes_active_registry_original_name_and_icon": (
            "active registry metadata refresh coverage"
        ),
        "test_reconcile_does_not_refresh_removed_scene_domain_metadata": (
            "removed scene metadata stale coverage"
        ),
        "metadata_updated=1": "active metadata updated diagnostics coverage",
    },
    "tests/test_entity_lifecycle_reconcile_entity_id.py": {
        "test_reconcile_renames_legacy_channel_entity_ids": (
            "legacy entity-id migration coverage"
        ),
        "test_reconcile_preserves_user_named_legacy_entity_id": (
            "user-named entity-id preservation coverage"
        ),
        "new_entity_id": "registry entity-id rename assertion",
        "chu_fang_shuang_jian_kai_guan_zuo_jian": (
            "friendly entity-id channel assertion"
        ),
    },
    "tests/test_entity_lifecycle_reconcile_property_entity_id.py": {
        "test_reconcile_renames_legacy_property_control_entity_ids": (
            "legacy property helper entity-id migration coverage"
        ),
        "test_reconcile_preserves_user_named_legacy_property_entity_id": (
            "user-named property entity-id preservation coverage"
        ),
        "默认渐变时长": "official property label metadata assertion",
        "select.cai_guang_deng_shi_fou_kai_qi_shan_duan": (
            "friendly property helper entity-id assertion"
        ),
    },
    "tests/test_entity_lifecycle_reconcile_display.py": {
        "test_reconcile_marks_extra_catalog_double_switch_channel_stale_and_updates_names": (
            "generated switch channel display-name cleanup coverage"
        ),
        "test_reconcile_clears_generated_single_light_original_name": (
            "generated single-light display-name cleanup coverage"
        ),
        "左键": "friendly positional switch channel assertion",
        "照明": "legacy generated light name fixture",
    },
    "tests/test_registry_cleanup_service.py": {
        "test_cleanup_registry_service_dry_run_returns_audit_id": (
            "cleanup service dry-run coverage"
        ),
        "test_cleanup_registry_service_confirm_disables_stale_entities": (
            "cleanup service confirm disable coverage"
        ),
        "test_cleanup_registry_service_disables_entities_excluded_by_import_filter": (
            "cleanup service filtered-device confirm coverage"
        ),
        "test_cleanup_registry_service_rejects_mismatched_audit_id": (
            "cleanup service stale result mismatch coverage"
        ),
        "test_cleanup_registry_service_rejects_missing_user_context": (
            "cleanup service explicit admin context coverage"
        ),
        "test_cleanup_registry_service_preserves_user_disabled_stale_entity": (
            "cleanup service user-disabled stale entity preservation coverage"
        ),
        "RegistryEntryDisabler.USER": (
            "cleanup service real user-disabled registry marker coverage"
        ),
        "ERROR_ADMIN_CONTEXT_REQUIRED": (
            "cleanup service missing-admin-context error contract"
        ),
        "call_cleanup_registry": "cleanup service helper usage",
        "removed_entity_ids == []": "cleanup service never removes registry entries",
    },
    "tests/test_registry_cleanup_service_privacy.py": {
        "test_cleanup_registry_service_rejects_stale_audit_after_topology_change": (
            "cleanup service topology-change stale audit rejection coverage"
        ),
        "test_cleanup_registry_service_response_and_logs_are_identifier_safe": (
            "cleanup service response/log identifier redaction coverage"
        ),
        "stale_entities == 2": "cleanup service changed stale-set rejection assertion",
        "secret-device-identifier": "cleanup service device identifier privacy marker",
        "removed_entity_ids == []": "cleanup privacy no-removal coverage",
    },
    "tests/test_entity_lifecycle.py": {
        "test_collect_active_entity_keys_projects_cloud_scenes_as_buttons_only": (
            "cloud-scene button-only active key coverage"
        ),
        "test_entity_registry_reconcile_diagnostics_ignores_foreign_summary": (
            "diagnostics summary type guard coverage"
        ),
    },
    "tests/test_repair_issues.py": {
        "test_create_topology_changed_issue_uses_aggregate_counts": (
            "aggregate Repairs issue coverage"
        ),
        "test_create_topology_changed_issue_whitelists_diff_summary_fields": (
            "Repairs diff sanitizer coverage"
        ),
        "secret-token": "Repairs redaction regression marker",
        '"entry-1" not in create_issue.call_args.args[2]': (
            "Repairs issue id redaction assertion"
        ),
    },
    "tests/test_repair_issue_cleanup.py": {
        "test_create_topology_changed_issue_deletes_stale_entry_issues": (
            "stale Repairs issue cleanup coverage"
        ),
        "test_delete_topology_changed_issues_only_deletes_entry_topology_issues": (
            "entry-scoped Repairs cleanup coverage"
        ),
        "HASHED_ENTRY_SCOPE": "hashed Repairs issue cleanup fixture",
        "OTHER_HASHED_ENTRY_SCOPE": "other-entry hashed Repairs cleanup guard",
    },
    "tests/test_config_entry_unload.py": {
        "test_unload_entry": "config-entry unload cleanup coverage",
        "push_manager.async_stop.assert_awaited_once": (
            "push manager unload stop coverage"
        ),
        "test_unload_entry_keeps_runtime_when_platform_unload_fails": (
            "failed platform unload runtime preservation coverage"
        ),
        "test_unload_entry_keeps_runtime_when_push_stop_fails": (
            "failed push stop runtime preservation coverage"
        ),
        "test_unload_entry_keeps_runtime_when_client_disconnect_fails": (
            "failed client disconnect runtime preservation coverage"
        ),
        "push_manager.async_stop.assert_not_awaited": (
            "failed unload push manager preservation coverage"
        ),
        "client_mock.disconnect.assert_not_awaited": (
            "failed unload client preservation coverage"
        ),
    },
    "tests/test_config_entry_lifecycle.py": {
        "test_setup_entry_keeps_polling_when_live_runtime_initial_connect_fails": (
            "live WebSocket initial failure polling fallback coverage"
        ),
        "test_setup_entry_keeps_cloud_runtime_when_lan_start_fails": (
            "optional LAN startup failure cloud fallback coverage"
        ),
        '"last_error_type": "OSError"': "recoverable live startup error aggregation",
        "coordinator.set_lan_runtime.assert_called_once_with(None)": (
            "failed optional LAN runtime is not attached to coordinator"
        ),
        "forward_platforms.assert_awaited_once": (
            "platform setup continues after recoverable runtime startup failure"
        ),
    },
}


def check_lifecycle_contracts(component_root: Path) -> list[str]:
    """Ensure HA registry lifecycle behavior remains covered before release."""
    errors: list[str] = []
    for relative_path, required_tokens in LIFECYCLE_CONTRACT_TOKENS.items():
        path = component_root / relative_path
        if not path.exists():
            errors.append(f"lifecycle contract requires {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"{relative_path} missing {reason}: {token}")
    return errors
