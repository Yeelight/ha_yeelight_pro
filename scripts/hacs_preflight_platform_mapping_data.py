"""Platform mapping release-preflight contract tokens."""

from __future__ import annotations

PLATFORM_MAPPING_CONTRACT_TEST_TOKENS: dict[str, dict[str, str]] = {
    "test_platform_mapping_contract.py": {
        "platform_candidates_for_payload": "payload-derived HA platform candidates",
        "test_broad_cloud_light_contact_payload_maps_to_binary_and_sensor": (
            "broad cloud light contact payload mapping guard"
        ),
        "test_broad_cloud_light_sensor_payload_maps_to_sensor_only": (
            "broad cloud light sensor mapping guard"
        ),
        "test_registry_safe_read_only_properties_project_sensor_candidates": (
            "registry safe read-only sensor platform candidate coverage"
        ),
        "test_category_without_capability_evidence_does_not_project_platform": (
            "category-only platform projection rejection guard"
        ),
        "test_acrc_config_property_does_not_claim_remote_platform": (
            "documented auxiliary bool switch evidence guard"
        ),
    },
    "test_platform_mapping_logging.py": {
        "test_platform_candidate_logging_reports_matched_property_evidence": (
            "platform candidate matched-evidence debug log coverage"
        ),
        "test_platform_candidate_logging_reports_missing_capability_evidence": (
            "platform candidate missing-evidence debug log coverage"
        ),
        "test_platform_candidate_logging_reports_ignored_unknown_property": (
            "platform candidate ignored-property debug log coverage"
        ),
        "test_platform_candidate_logging_redacts_sensitive_property_keys": (
            "platform candidate sensitive-key redaction coverage"
        ),
        "missing_capability_evidence": "platform candidate stable missing reason",
        "missing_light_capability_evidence": (
            "platform candidate stable ignored light reason"
        ),
        "unknown_property": "platform candidate stable ignored unknown-property reason",
    },
}
