"""Release-preflight tokens for legacy local HA entrypoints."""

from __future__ import annotations

LEGACY_LOCAL_HA_ENTRYPOINT_TOKENS = {
    "test_actual_environment.py": {
        "verify_local_ha_main": "legacy actual-environment entrypoint delegates verifier",
        "scripts.verify_local_ha": "legacy actual-environment shared verifier import",
    },
    "test_complete_ha.py": {
        "verify_local_ha_main": "legacy complete-HA entrypoint delegates verifier",
        "scripts.verify_local_ha": "legacy complete-HA shared verifier import",
    },
    "test_functional.py": {
        "verify_local_ha_main": "legacy functional entrypoint delegates verifier",
        "scripts.verify_local_ha": "legacy functional shared verifier import",
    },
    "test_real_ha_environment.py": {
        "verify_local_ha_main": "legacy real-HA entrypoint delegates verifier",
        "scripts.verify_local_ha": "legacy real-HA shared verifier import",
    },
    "custom_components/yeelight_pro/tests/test_legacy_local_ha_entrypoints.py": {
        "ENTRYPOINTS": "legacy local HA entrypoint list coverage",
        "test_legacy_local_ha_entrypoint_delegates_to_shared_verifier": (
            "legacy local HA entrypoint verifier reuse coverage"
        ),
        "test_legacy_local_ha_entrypoint_help_imports_cleanly": (
            "legacy local HA entrypoint script-path coverage"
        ),
    },
}
