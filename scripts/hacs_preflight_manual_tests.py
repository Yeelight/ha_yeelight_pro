"""Release-preflight tokens for root-level manual HA smoke helpers."""

from __future__ import annotations

MANUAL_HA_TEST_TOKENS = {
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
}
