"""Runtime verifier contract token facade for local HA validation."""

from __future__ import annotations

from scripts.hacs_preflight_local_ha_runtime_sources import (
    LOCAL_HA_RUNTIME_SOURCE_TOKENS,
)
from scripts.hacs_preflight_local_ha_runtime_capability_sources import (
    LOCAL_HA_RUNTIME_CAPABILITY_SOURCE_TOKENS,
)
from scripts.hacs_preflight_local_ha_runtime_tests import (
    LOCAL_HA_RUNTIME_TEST_TOKENS,
)
from scripts.hacs_preflight_local_ha_runtime_verifier_sources import (
    LOCAL_HA_RUNTIME_VERIFIER_SOURCE_TOKENS,
)

LOCAL_HA_RUNTIME_CONTRACT_TOKENS = {
    "scripts/hacs_preflight_local_ha_runtime.py": {
        "LOCAL_HA_RUNTIME_CAPABILITY_SOURCE_TOKENS": (
            "runtime capability source token import"
        ),
        "LOCAL_HA_RUNTIME_SOURCE_TOKENS": "runtime source token import",
        "LOCAL_HA_RUNTIME_VERIFIER_SOURCE_TOKENS": (
            "runtime verifier source token import"
        ),
        "LOCAL_HA_RUNTIME_TEST_TOKENS": "runtime test token import",
        "LOCAL_HA_RUNTIME_CONTRACT_TOKENS": "runtime contract token facade",
    },
    **LOCAL_HA_RUNTIME_CAPABILITY_SOURCE_TOKENS,
    **LOCAL_HA_RUNTIME_SOURCE_TOKENS,
    **LOCAL_HA_RUNTIME_VERIFIER_SOURCE_TOKENS,
    **LOCAL_HA_RUNTIME_TEST_TOKENS,
}
