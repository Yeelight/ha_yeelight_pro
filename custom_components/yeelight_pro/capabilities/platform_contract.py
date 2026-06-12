"""Home Assistant platform mapping contract for Yeelight IoT payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .ha_core_platforms import HA_CORE_PLATFORMS
from .platform_candidate_projection import (
    platform_candidates_for_payload,
)
from .platform_contract_data import (
    DEFAULT_UNSUPPORTED_EVIDENCE,
    PRIMARY_PLATFORM_CONTRACT_ROWS,
)

PlatformSupportStatus = Literal["supported", "experimental", "unsupported"]
PlatformSummaryStatus = Literal["supported", "diagnostic", "unsupported"]


@dataclass(frozen=True, slots=True)
class PlatformContract:
    """One Home Assistant platform mapping decision."""

    platform: str
    status: PlatformSupportStatus
    evidence: str


_PRIMARY_PLATFORM_CONTRACTS: tuple[PlatformContract, ...] = tuple(
    PlatformContract(platform, status, evidence)
    for platform, status, evidence in PRIMARY_PLATFORM_CONTRACT_ROWS
)
PLATFORM_CONTRACTS: tuple[PlatformContract, ...] = (
    _PRIMARY_PLATFORM_CONTRACTS
    + tuple(
        PlatformContract(platform, "unsupported", DEFAULT_UNSUPPORTED_EVIDENCE)
        for platform in sorted(
            HA_CORE_PLATFORMS - {item.platform for item in _PRIMARY_PLATFORM_CONTRACTS}
        )
    )
)


def platform_contracts() -> tuple[PlatformContract, ...]:
    """Return the fixed HA platform mapping support matrix."""
    return PLATFORM_CONTRACTS


def primary_platform_for_payload(payload: Mapping[str, Any]) -> str | None:
    """Return the first supported primary candidate for a runtime payload."""
    candidates = platform_candidates_for_payload(payload)
    return candidates[0] if candidates else None


def platform_mapping_summary() -> tuple[dict[str, str], ...]:
    """Return a JSON-safe support matrix for diagnostics or tests."""
    return tuple(
        {
            "platform": item.platform,
            "status": _support_status(item.status),
            "reason": item.evidence,
        }
        for item in PLATFORM_CONTRACTS
    )


def _support_status(status: str) -> PlatformSummaryStatus:
    if status == "experimental":
        return "diagnostic"
    if status == "unsupported":
        return "unsupported"
    return "supported"


__all__ = [
    "HA_CORE_PLATFORMS",
    "PLATFORM_CONTRACTS",
    "PlatformContract",
    "PlatformSummaryStatus",
    "PlatformSupportStatus",
    "platform_candidates_for_payload",
    "platform_contracts",
    "platform_mapping_summary",
    "primary_platform_for_payload",
]
