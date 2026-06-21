"""Topology coverage helpers for private-house audit reports."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, cast

from custom_components.yeelight_pro.entity_candidate_topology import iter_topology_entity_candidates
from scripts.private_house_audit.coverage_model import TopologyCoverage
from scripts.private_house_audit.report_samples import (
    actual_row_role,
    candidate_role,
    candidate_samples,
    entity_domain,
)



def _topology_coverage(
    *,
    entry_data: Mapping[str, Any],
    house_id: int | None,
    registry_entries: Mapping[str, Mapping[str, Any]],
    areas: Sequence[Mapping[str, Any]],
    rooms: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
    houses: Sequence[Mapping[str, Any]],
    scenes: Sequence[Mapping[str, Any]],
    analytics_enabled: bool,
) -> list[TopologyCoverage]:
    """Return coverage rows for room/area/group/scene/house helper entities."""
    coordinator = _TopologyCandidateCoordinator(
        entry_data=entry_data,
        house_id=house_id,
        areas=areas,
        rooms=rooms,
        groups=groups,
        houses=houses,
        scenes=scenes,
    )
    candidates = list(
        iter_topology_entity_candidates(
            cast(Any, coordinator),
            analytics_enabled=analytics_enabled,
        )
    )
    by_source: dict[str, list[Any]] = {}
    for candidate in candidates:
        by_source.setdefault(candidate.source, []).append(candidate)

    rows: list[TopologyCoverage] = []
    for source, source_candidates in sorted(by_source.items()):
        expected_ids = {item.unique_id: item for item in source_candidates}
        actual_rows = {
            unique_id: registry_entries[unique_id]
            for unique_id in expected_ids
            if unique_id in registry_entries
        }
        missing = [
            expected_ids[unique_id]
            for unique_id in expected_ids
            if unique_id not in actual_rows
        ]
        rows.append(
            TopologyCoverage(
                source=source,
                expected_total=len(expected_ids),
                actual_total=len(actual_rows),
                missing_total=len(missing),
                expected_platforms=dict(sorted(Counter(
                    item.platform for item in source_candidates
                ).items())),
                actual_platforms=dict(sorted(Counter(
                    domain
                    for row in actual_rows.values()
                    if (domain := entity_domain(row))
                ).items())),
                missing_platforms=dict(sorted(Counter(
                    item.platform for item in missing
                ).items())),
                expected_roles=dict(sorted(Counter(
                    candidate_role(item) for item in source_candidates
                ).items())),
                actual_roles=dict(sorted(Counter(
                    actual_row_role(row) for row in actual_rows.values()
                ).items())),
                missing_roles=dict(sorted(Counter(
                    candidate_role(item) for item in missing
                ).items())),
                expected_samples=candidate_samples(source_candidates),
                missing_samples=candidate_samples(missing),
            )
        )
    return rows


class _TopologyCandidateCoordinator:
    """Minimal coordinator shape for topology candidate projection."""

    def __init__(
        self,
        *,
        entry_data: Mapping[str, Any],
        house_id: int | None,
        areas: Sequence[Mapping[str, Any]],
        rooms: Sequence[Mapping[str, Any]],
        groups: Sequence[Mapping[str, Any]],
        houses: Sequence[Mapping[str, Any]],
        scenes: Sequence[Mapping[str, Any]],
    ) -> None:
        self.entry_data = dict(entry_data)
        self.house_id = house_id
        self.areas = [dict(item) for item in areas if isinstance(item, Mapping)]
        self.rooms = [dict(item) for item in rooms if isinstance(item, Mapping)]
        self.groups = [dict(item) for item in groups if isinstance(item, Mapping)]
        self.houses = [dict(item) for item in houses if isinstance(item, Mapping)]
        self.scenes = [dict(item) for item in scenes if isinstance(item, Mapping)]
        self.data: Mapping[Any, Mapping[str, Any]] = {}
        self.hide_unknown_entities = True

__all__ = ["_topology_coverage"]
