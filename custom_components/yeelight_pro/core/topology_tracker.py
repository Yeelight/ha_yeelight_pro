"""Track topology generations for Yeelight Pro coordinator snapshots."""

from __future__ import annotations

from typing import Any, Mapping

from .topology_diff import (
    TopologyDiffSummary,
    build_topology_snapshot,
    empty_topology_diff,
    summarize_topology_diff,
    topology_snapshot_signature,
)


class TopologyTracker:
    """Maintain generation and diff state for entity/device topology."""

    def __init__(self) -> None:
        self._generation = 0
        self._signature: tuple[Any, ...] | None = None
        self._snapshot: dict[str, dict[str, tuple[Any, ...]]] | None = None
        self._last_diff = empty_topology_diff()

    @property
    def generation(self) -> int:
        """Return the current topology generation."""
        return self._generation

    @property
    def diff_summary(self) -> TopologyDiffSummary:
        """Return the latest sanitized topology diff summary."""
        return self._last_diff

    def update(
        self,
        *,
        devices: Mapping[Any, Mapping[str, Any]],
        gateways: Mapping[Any, Mapping[str, Any]],
        areas: list[dict[str, Any]],
        rooms: list[dict[str, Any]],
        groups: list[dict[str, Any]],
        scenes: list[dict[str, Any]],
        automations: list[dict[str, Any]],
    ) -> None:
        """Update generation only when topology signature changes."""
        snapshot = build_topology_snapshot(
            devices=devices,
            gateways=gateways,
            areas=areas,
            rooms=rooms,
            groups=groups,
            scenes=scenes,
            automations=automations,
        )
        signature = topology_snapshot_signature(snapshot)
        if signature == self._signature:
            self._last_diff = empty_topology_diff(
                previous_generation=self._generation,
                current_generation=self._generation,
            )
            return

        previous_snapshot = self._snapshot
        previous_generation = self._generation
        self._signature = signature
        self._snapshot = snapshot
        self._generation += 1
        self._last_diff = summarize_topology_diff(
            previous_snapshot,
            snapshot,
            previous_generation=previous_generation,
            current_generation=self._generation,
        )

