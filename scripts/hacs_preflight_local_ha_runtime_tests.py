"""Runtime test contract token facade for local HA validation."""

from __future__ import annotations

from scripts.hacs_preflight_local_ha_runtime_core_tests import (
    LOCAL_HA_RUNTIME_CORE_TEST_TOKENS,
)
from scripts.hacs_preflight_local_ha_runtime_verifier_tests import (
    LOCAL_HA_RUNTIME_VERIFIER_TEST_TOKENS,
)

LOCAL_HA_RUNTIME_TEST_TOKENS = {
    "scripts/hacs_preflight_local_ha_runtime_tests.py": {
        "LOCAL_HA_RUNTIME_CORE_TEST_TOKENS": "runtime core test token import",
        "LOCAL_HA_RUNTIME_VERIFIER_TEST_TOKENS": (
            "runtime verifier test token import"
        ),
        "LOCAL_HA_RUNTIME_TEST_TOKENS": "runtime test token facade",
    },
    **LOCAL_HA_RUNTIME_CORE_TEST_TOKENS,
    **LOCAL_HA_RUNTIME_VERIFIER_TEST_TOKENS,
}
