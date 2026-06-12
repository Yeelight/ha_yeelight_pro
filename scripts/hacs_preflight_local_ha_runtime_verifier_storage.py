"""Storage verifier source contract tokens for local HA validation."""

from __future__ import annotations

LOCAL_HA_RUNTIME_VERIFIER_STORAGE_TOKENS = {
    "scripts/hacs_preflight_local_ha_runtime_verifier_storage.py": {
        "LOCAL_HA_RUNTIME_VERIFIER_STORAGE_TOKENS": (
            "storage verifier source token registry"
        ),
        "scripts/local_ha_verification/storage.py": (
            "storage verifier source token coverage"
        ),
        "scripts/local_ha_verification/storage_device_quality.py": (
            "storage device quality verifier source token coverage"
        ),
        "scripts/local_ha_verification/storage_entity_quality.py": (
            "storage entity quality verifier source token coverage"
        ),
        "scripts/local_ha_verification/storage_entries.py": (
            "storage entry verifier source token coverage"
        ),
        "scripts/local_ha_verification/storage_helpers.py": (
            "storage helper verifier source token coverage"
        ),
    },
    "scripts/local_ha_verification/storage.py": {
        "safe_storage_items": "sanitized storage read failure handling",
        "verify_device_registry_quality": "device registry quality verifier call",
        "verify_entity_registry_quality": "entity registry quality verifier call",
        "verify_config_entry_migration": "config entry migration verifier call",
        "verify_config_entry_unique_ids": "config entry unique-id verifier call",
        "verify_config_entry_options": "config entry option verifier call",
        "verify_platform_options_alignment": "platform/options verifier call",
        "verify_storage": "aggregate HA storage verification",
        "verify_product_schema_cache": "product schema privacy scan",
        "sensitive_cache_hits": "structured schema cache privacy scan",
        "schema values are not objects": "schema cache object-shape guard",
        "product_schema_cache": "schema cache stability metric",
        "retained_entity_domains": "retained registry domain stability metric",
        "entity_registry_disabled_by": "cleanup B retained registry stability metric",
    },
    "scripts/local_ha_verification/storage_device_quality.py": {
        "verify_device_registry_quality": "source device registry quality gate",
        "GENERIC_SOURCE_MODELS": "generic device model denylist",
        "is_source_device": "source device identifier classifier",
        "device_registry_quality": "device registry quality metric",
        "missing friendly names": "device friendly-name failure guard",
        "generic model labels": "generic model failure guard",
        "generated house helper names": "house placeholder failure guard",
        "historical runtime model_id values": "runtime model-id warning guard",
    },
    "scripts/local_ha_verification/storage_entity_quality.py": {
        "verify_entity_registry_quality": "entity registry quality gate",
        "fail_enabled_legacy_scene_entities": "legacy scene stale-entry gate",
        "source_device_id_from_unique_id": "device-backed unique-id parser",
        "legacy native scene registry entries": "legacy scene cleanup failure guard",
        "entity registry categories": "device-page category distribution fact",
        "entity_friendly_names": "friendly entity-name stability metric",
        "UNFRIENDLY_PROPERTY_NAMES": "raw English property-name denylist",
        "raw channel/action/property names": (
            "raw channel/action/property-name failure guard"
        ),
        "entity_device_links": "device-backed entity link metric",
        "yeelight_restore_state": "Yeelight restore-state stability metric",
        "restored states are unavailable": "unavailable restore-state failure guard",
    },
    "scripts/local_ha_verification/storage_entries.py": {
        "REQUIRED_CONFIG_ENTRY_DATA_KEYS": "config entry required data keys",
        "OPTIONAL_CONFIG_ENTRY_DATA_KEYS": "config entry optional data keys",
        "verify_config_entry_titles": "config entry title verifier call",
        "verify_config_entry_migration": "config entry migration status check",
        "verify_config_entry_unique_ids": "config entry unique-id isolation check",
        "_expected_config_entry_title": "config entry expected title helper",
        "_expected_config_entry_unique_id": "config entry expected unique-id helper",
        "_expected_entry_version": "config entry version constant parser",
        "config_entry_unique_ids": "config entry unique-id stability metric",
        "config_entry_titles": "config entry title stability metric",
        "config_entry_versions": "config entry version stability metric",
        "optional_config_entry_missing_keys": "optional config data metric key",
    },
    "scripts/local_ha_verification/storage_helpers.py": {
        "storage_path": "HA storage path helper",
        "read_json": "storage JSON object reader",
        "storage_items": "storage list item reader",
        "safe_storage_items": "sanitized storage read helper",
        "sensitive_cache_hits": "structured schema cache privacy helper",
        "SENSITIVE_CACHE_MARKERS": "sensitive key marker denylist use",
        "SENSITIVE_CACHE_VALUE_PATTERNS": "sensitive value pattern denylist use",
    },
}
