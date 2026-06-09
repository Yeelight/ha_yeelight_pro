"""Dynamic entity filter preflight data for Yeelight Pro."""

from __future__ import annotations

DYNAMIC_ENTITY_FILTER_CONTRACT_TOKENS = {
    "dynamic_entities.py": {
        "CONF_DEVICE_IMPORT_FILTER": "runtime filter option lookup",
        "matches_device_import_filter": "shared device filter semantics",
        "registry_entry is None": "filter applies only to new registry entries",
        "_should_skip_registered_entity": "user-disabled registry guard",
        "_entity_device_payload": "source device lookup for filter decisions",
    },
    "tests/test_dynamic_entity_filters.py": {
        "include_filter_blocks_unmatched_new_devices": "include rule runtime gate",
        "exclude_filter_blocks_matched_new_devices": "exclude rule runtime gate",
        "filter_uses_source_device_id": "event source device id coverage",
        "filter_uses_unique_id_fallback": "strict unique-id fallback coverage",
        "filter_is_disabled_without_registry_context": "registry context safety",
        "filter_preserves_non_device_entities_with_registry": (
            "auxiliary entity preservation with registry context"
        ),
        "filter_does_not_restore_user_disabled_entry": "user-disabled guard coverage",
        "filter_allows_existing_registry_restore": "existing registry restore coverage",
    },
}
