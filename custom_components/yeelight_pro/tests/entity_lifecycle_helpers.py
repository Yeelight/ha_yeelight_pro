"""Shared helpers for entity lifecycle tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.yeelight_pro import entity_lifecycle


class FakeEntityRegistry:
    """Minimal entity registry double that records registry mutations."""

    def __init__(
        self,
        entries: list[SimpleNamespace],
        *,
        global_entries: list[SimpleNamespace] | None = None,
        rejected_new_entity_ids: set[str] | None = None,
    ) -> None:
        self.entries = entries
        self.entities = {
            entry.entity_id: entry for entry in [*entries, *(global_entries or [])]
        }
        self.rejected_new_entity_ids = set(rejected_new_entity_ids or ())
        self.removed_entity_ids: list[str] = []
        self.updated_entities: list[tuple[str, dict[str, object | None]]] = []

    def async_remove(self, entity_id: str) -> None:
        self.removed_entity_ids.append(entity_id)

    def async_update_entity(
        self,
        entity_id: str,
        *,
        disabled_by: object | None = None,
        new_entity_id: str | None = None,
        **kwargs: object | None,
    ) -> SimpleNamespace:
        update_kwargs = dict(kwargs)
        if new_entity_id in self.rejected_new_entity_ids:
            raise ValueError("new entity_id already in use")
        if new_entity_id is not None:
            update_kwargs["new_entity_id"] = new_entity_id
        update_kwargs["disabled_by"] = disabled_by
        self.updated_entities.append((entity_id, update_kwargs))
        for entry in self.entries:
            if entry.entity_id == entity_id:
                for key, value in update_kwargs.items():
                    if key == "new_entity_id":
                        entry.entity_id = value
                    else:
                        setattr(entry, key, value)
                return entry
        return SimpleNamespace(entity_id=entity_id, **update_kwargs)


def lifecycle_coordinator(
    *,
    data: dict[int, dict[str, object]] | None = None,
    scenes: list[dict[str, str]] | None = None,
    options: dict[str, object] | None = None,
) -> SimpleNamespace:
    """Build the coordinator shape required by entity lifecycle helpers."""
    return SimpleNamespace(
        data=data or {},
        scenes=scenes or [],
        groups=[],
        rooms=[],
        areas=[],
        houses=[],
        house_id=None,
        analytics_enabled=False,
        analytics_data=None,
        hide_unknown_entities=False,
        options=options or {},
    )


def reconcile_diagnostics(
    *,
    active: int,
    registry_entries: int,
    stale: int,
    pending_stale: int,
    restored: int = 0,
    metadata_updated: int = 0,
) -> dict[str, int]:
    """Build expected reconcile diagnostics with explicit changed fields."""
    return {
        "active": active,
        "registry_entries": registry_entries,
        "stale": stale,
        "pending_stale": pending_stale,
        "disabled": 0,
        "restored": restored,
        "metadata_updated": metadata_updated,
    }


def registry_entry(
    *,
    unique_id: str,
    entity_id: str,
    domain: str,
    disabled_by: object | None = None,
    original_name: str | None = None,
    original_icon: str | None = None,
    has_entity_name: bool | None = True,
    entity_category: object | None = None,
    name: str | None = None,
) -> SimpleNamespace:
    """Build a focused registry entry without depending on HA internals."""
    return SimpleNamespace(
        platform="yeelight_pro",
        unique_id=unique_id,
        entity_id=entity_id,
        domain=domain,
        disabled_by=disabled_by,
        original_name=original_name,
        original_icon=original_icon,
        name=name,
        has_entity_name=has_entity_name,
        entity_category=entity_category,
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
