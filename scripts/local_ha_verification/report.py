"""Verification report models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VerificationReport:
    """Collect local HA verification output."""

    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)

    def fact(self, message: str) -> None:
        """Record a verified fact."""
        self.facts.append(message)

    def warn(self, message: str) -> None:
        """Record a non-blocking warning."""
        self.warnings.append(message)

    def fail(self, message: str) -> None:
        """Record a blocking failure."""
        self.failures.append(message)

    def metric(self, name: str, value: object) -> None:
        """Record a stable aggregate metric for multi-run drift checks."""
        self.metrics[name] = value

    @property
    def ok(self) -> bool:
        """Return true when no blocking failures were collected."""
        return not self.failures
