"""Shared helpers for entity lifecycle tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.yeelight_pro import entity_lifecycle


class FakeEntityRegistry:
    """Minimal entity registry double that records registry mutations."""

    def __init__(self, entries: list[SimpleNamespace]) -> None:
        self.entries = entries
        self.removed_entity_ids: list[str] = []
        self.updated_entities: list[tuple[str, object | None]] = []

    def async_remove(self, entity_id: str) -> None:
        self.removed_entity_ids.append(entity_id)

    def async_update_entity(
        self,
        entity_id: str,
        *,
        disabled_by: object | None = None,
    ) -> SimpleNamespace:
        self.updated_entities.append((entity_id, disabled_by))
        for entry in self.entries:
            if entry.entity_id == entity_id:
                entry.disabled_by = disabled_by
                return entry
        return SimpleNamespace(entity_id=entity_id, disabled_by=disabled_by)


def lifecycle_coordinator(
    *,
    data: dict[int, dict[str, object]] | None = None,
    scenes: list[dict[str, str]] | None = None,
) -> SimpleNamespace:
    """Build the coordinator shape required by entity lifecycle helpers."""
    return SimpleNamespace(
        data=data or {},
        scenes=scenes or [],
        automations=[],
        groups=[],
        house_id=None,
        hide_unknown_entities=False,
    )


def registry_entry(
    *,
    unique_id: str,
    entity_id: str,
    domain: str,
    disabled_by: object | None = None,
) -> SimpleNamespace:
    """Build a focused registry entry without depending on HA internals."""
    return SimpleNamespace(
        platform="yeelight_pro",
        unique_id=unique_id,
        entity_id=entity_id,
        domain=domain,
        disabled_by=disabled_by,
    )


def patch_entity_registry(
    monkeypatch: pytest.MonkeyPatch,
    registry: FakeEntityRegistry,
) -> None:
    """Patch Home Assistant entity registry helpers for lifecycle tests."""
    monkeypatch.setattr(entity_lifecycle.er, "async_get", lambda hass: registry)
    monkeypatch.setattr(
        entity_lifecycle.er,
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: entity_registry.entries,
    )
