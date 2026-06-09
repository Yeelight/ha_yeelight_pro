"""Local HA verification release preflight data facade."""

from __future__ import annotations

from scripts.hacs_preflight_local_ha_release import (
    LOCAL_HA_RELEASE_CONTRACT_TOKENS,
)
from scripts.hacs_preflight_local_ha_runtime import (
    LOCAL_HA_RUNTIME_CONTRACT_TOKENS,
)

VERIFY_LOCAL_HA_CONTRACT_TOKENS = {
    **LOCAL_HA_RELEASE_CONTRACT_TOKENS,
    **LOCAL_HA_RUNTIME_CONTRACT_TOKENS,
}
