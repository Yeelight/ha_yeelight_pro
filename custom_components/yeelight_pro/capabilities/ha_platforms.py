"""Home Assistant platform boundary facade for Yeelight Pro."""

from __future__ import annotations

from .ha_core_platforms import HA_CORE_PLATFORMS
from .platform_contract import PlatformContract as HAPlatformMapping
from .platform_contract import platform_contracts


SUPPORTED_HA_PLATFORMS: frozenset[str] = frozenset(
    item.platform for item in platform_contracts() if item.status == "supported"
)

EXPERIMENTAL_HA_PLATFORMS: frozenset[str] = frozenset()

UNSUPPORTED_HA_PLATFORMS: frozenset[str] = frozenset(
    item.platform for item in platform_contracts() if item.status == "unsupported"
)

HA_PLATFORM_MAPPING_MATRIX = platform_contracts()
MAPPED_HA_PLATFORMS: frozenset[str] = (
    SUPPORTED_HA_PLATFORMS | EXPERIMENTAL_HA_PLATFORMS | UNSUPPORTED_HA_PLATFORMS
)


def ha_platform_mapping_status(platform: str) -> str | None:
    """Return mapping status for a Home Assistant platform."""
    for item in HA_PLATFORM_MAPPING_MATRIX:
        if item.platform == platform:
            if item.platform in EXPERIMENTAL_HA_PLATFORMS:
                return "experimental"
            return item.status
    if platform in UNSUPPORTED_HA_PLATFORMS:
        return "unsupported"
    return None


__all__ = [
    "EXPERIMENTAL_HA_PLATFORMS",
    "HA_CORE_PLATFORMS",
    "HA_PLATFORM_MAPPING_MATRIX",
    "HAPlatformMapping",
    "MAPPED_HA_PLATFORMS",
    "SUPPORTED_HA_PLATFORMS",
    "UNSUPPORTED_HA_PLATFORMS",
    "ha_platform_mapping_status",
]
