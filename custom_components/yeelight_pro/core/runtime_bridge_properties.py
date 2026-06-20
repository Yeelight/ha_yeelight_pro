"""Property-update application mixin for Yeelight Pro runtime bridge."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import logging
from typing import Any

from .lan_sensor_values import normalize_lan_device_params
from .lan_topology_specs import (
    NODE_TYPE_AREA,
    NODE_TYPE_GROUP,
    NODE_TYPE_HOUSE,
    NODE_TYPE_ROOM,
)
from .runtime_bridge_nodes import (
    candidate_matches_node_type,
    collection_contains_node,
    node_type_collections,
    safe_node_id_candidate_diagnostics,
    safe_param_keys,
    selected_candidate_field,
    stable_digest,
    unknown_update_reason,
)
from .runtime_bridge_types import (
    MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS,
    RuntimePropertyUpdate,
    RuntimePropertyUpdateSummary,
    RuntimeUpdateContext,
)
from .runtime_state import (
    merge_runtime_state_into_group_payloads,
    merge_runtime_state_into_node_payloads,
    online_from_params,
)

_LOGGER = logging.getLogger(__name__)


class RuntimePropertyApplyMixin:
    """Apply property updates to devices, groups, and topology nodes."""

    def apply_property_updates(
        self,
        updates: Sequence[RuntimePropertyUpdate],
    ) -> bool:
        """合并属性更新，返回是否实际写入过运行时状态。"""
        changed = False
        input_updates = 0
        empty_param_updates = 0
        applied = 0
        unknown = 0
        group_updates = 0
        topology_node_updates = 0
        routed_updates = 0
        applied_node_samples: list[dict[str, Any]] = []
        unknown_node_samples: list[dict[str, Any]] = []
        affected_contexts: set[RuntimeUpdateContext] = set()
        for raw_update in updates:
            input_updates += 1
            update = self._resolve_update_node(raw_update)
            if not update.params:
                empty_param_updates += 1
                continue
            params = self._normalized_params(update)
            loaded_payload = self._loaded_payload(update.node_id)
            matched_collections = self._matching_collections(update.node_id)
            if _is_group_update(update, loaded_payload, matched_collections):
                group_updates += 1
                routed_updates += 1
                if len(applied_node_samples) < MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS:
                    applied_node_samples.append(
                        self._applied_update_sample(update, params, ["groups"])
                    )
                affected_contexts.add(("group", str(update.node_id)))
                changed = (
                    self._groups is not None
                    and merge_runtime_state_into_group_payloads(
                        self._groups,
                        group_id=update.node_id,
                        params=params,
                        online=online_from_params(params),
                    )
                ) or changed
                continue
            collection = self._topology_node_collection(
                update,
                loaded_payload,
                matched_collections,
            )
            if collection is not None:
                topology_node_updates += 1
                routed_updates += 1
                if len(applied_node_samples) < MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS:
                    applied_node_samples.append(
                        self._applied_update_sample(
                            update,
                            params,
                            matched_collections,
                        )
                    )
                affected_contexts.add(
                    _topology_update_context(
                        update.node_type,
                        update.node_id,
                        matched_collections,
                    )
                )
                changed = merge_runtime_state_into_node_payloads(
                    collection,
                    node_id=update.node_id,
                    params=params,
                    online=online_from_params(params),
                ) or changed
                continue
            if loaded_payload is None:
                unknown += 1
                if len(unknown_node_samples) < MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS:
                    unknown_node_samples.append(
                        self._unknown_update_sample(update, params)
                    )
                self._runtime_state.store_update(
                    update.node_id,
                    params,
                    devices=self._devices,
                    gateways=self._gateways,
                    data=self._data,
                    rebuild_canonical=self._rebuild_canonical,
                    groups=self._groups,
                )
                affected_contexts.add(("device", str(update.node_id)))
                changed = True
                continue
            changed = True
            applied += 1
            routed_updates += 1
            if len(applied_node_samples) < MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS:
                applied_node_samples.append(
                    self._applied_update_sample(
                        update,
                        params,
                        matched_collections,
                    )
                )
            self._runtime_state.store_update(
                update.node_id,
                params,
                devices=self._devices,
                gateways=self._gateways,
                data=self._data,
                rebuild_canonical=self._rebuild_canonical,
                groups=self._groups,
            )
            affected_contexts.add(("device", str(update.node_id)))
        self.last_apply_summary = RuntimePropertyUpdateSummary(
            input_updates=input_updates,
            empty_param_updates=empty_param_updates,
            applied_device_updates=applied,
            unknown_device_updates=unknown,
            group_updates=group_updates,
            topology_node_updates=topology_node_updates,
            routed_updates=routed_updates,
            changed=changed,
            device_import_filter_enabled=self._device_import_filter_enabled,
            applied_node_samples=tuple(applied_node_samples),
            unknown_node_samples=tuple(unknown_node_samples),
            affected_contexts=tuple(sorted(affected_contexts)),
        )
        if applied or unknown or group_updates or topology_node_updates:
            _LOGGER.debug(
                "Applied Yeelight Pro runtime property updates: "
                "applied=%s unknown_nodes=%s group_updates=%s topology_node_updates=%s "
                "unknown_samples=%s",
                applied,
                unknown,
                group_updates,
                topology_node_updates,
                unknown_node_samples,
            )
        return changed

    def _resolve_update_node(
        self,
        update: RuntimePropertyUpdate,
    ) -> RuntimePropertyUpdate:
        """Resolve alternate node-id aliases when only one candidate is loaded."""
        if not update.node_id_candidates:
            return update

        typed_match = self._typed_candidate_match(update)
        if typed_match is not None:
            field_name, resolved_id = typed_match
            if resolved_id != update.node_id:
                _LOGGER.debug(
                    "Resolved Yeelight Pro runtime update node by type: "
                    "selected_hash=%s node_type=%s alias_field=%s alias_hash=%s",
                    stable_digest(update.node_id),
                    update.node_type,
                    field_name,
                    stable_digest(resolved_id),
                )
                return RuntimePropertyUpdate(
                    node_id=resolved_id,
                    node_type=update.node_type,
                    params=update.params,
                    node_id_candidates=update.node_id_candidates,
                )
            return update

        selected_field = selected_candidate_field(update)
        if candidate_matches_node_type(
            selected_field,
            self._matching_collections(update.node_id),
            update.node_type,
        ):
            return update

        matches: list[tuple[str, int]] = []
        seen: set[int] = set()
        for field_name, candidate_id in update.node_id_candidates:
            if candidate_id == update.node_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            if candidate_matches_node_type(
                field_name,
                self._matching_collections(candidate_id),
                update.node_type,
            ):
                matches.append((field_name, candidate_id))
        if len(matches) != 1:
            return update

        field_name, resolved_id = matches[0]
        _LOGGER.debug(
            "Resolved Yeelight Pro runtime update node alias: "
            "selected_hash=%s alias_field=%s alias_hash=%s",
            stable_digest(update.node_id),
            field_name,
            stable_digest(resolved_id),
        )
        return RuntimePropertyUpdate(
            node_id=resolved_id,
            node_type=update.node_type,
            params=update.params,
            node_id_candidates=update.node_id_candidates,
        )

    def _typed_candidate_match(
        self,
        update: RuntimePropertyUpdate,
    ) -> tuple[str, int] | None:
        """Return a unique candidate that matches the documented node type."""
        expected_collections = node_type_collections(update.node_type)
        if not expected_collections:
            return None

        matches: list[tuple[str, int]] = []
        seen: set[int] = set()
        for field_name, candidate_id in update.node_id_candidates:
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            candidate_collections = self._matching_collections(candidate_id)
            if candidate_matches_node_type(
                field_name,
                candidate_collections,
                update.node_type,
                expected_collections=expected_collections,
            ):
                matches.append((field_name, candidate_id))
        if len(matches) != 1:
            return None
        return matches[0]

    def _normalized_params(self, update: RuntimePropertyUpdate) -> dict[str, Any]:
        """Return params normalized against the loaded device metadata."""
        device = self._loaded_payload(update.node_id)
        lan_type = device.get("lan_type") if isinstance(device, Mapping) else None
        return normalize_lan_device_params(update.params, lan_type=lan_type)

    def _loaded_payload(self, node_id: int) -> Mapping[str, Any] | None:
        """Return the currently loaded payload for a property update."""
        for source in (self._devices, self._gateways, self._data):
            payload = source.get(node_id)
            if isinstance(payload, Mapping):
                return payload
        return None

    def _topology_node_collection(
        self,
        update: RuntimePropertyUpdate,
        loaded_payload: Mapping[str, Any] | None,
        matched_collections: Sequence[str],
    ) -> list[dict[str, Any]] | None:
        """Return the topology collection for room/area/house property updates."""
        if update.node_type == NODE_TYPE_ROOM:
            return self._rooms
        if update.node_type == NODE_TYPE_AREA:
            return self._areas
        if update.node_type == NODE_TYPE_HOUSE:
            return self._houses
        if loaded_payload is not None:
            return None
        if matched_collections == ["rooms"]:
            return self._rooms
        if matched_collections == ["areas"]:
            return self._areas
        if matched_collections == ["houses"]:
            return self._houses
        return None

    def _unknown_update_sample(
        self,
        update: RuntimePropertyUpdate,
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return a redacted sample explaining why one update was not loaded."""
        matched_collections = self._matching_collections(update.node_id)
        return {
            "node_id_hash": stable_digest(update.node_id),
            "node_type": update.node_type,
            "param_keys": safe_param_keys(params),
            "matched_collections": matched_collections,
            "reason": unknown_update_reason(matched_collections),
            "device_import_filter_enabled": self._device_import_filter_enabled,
            **safe_node_id_candidate_diagnostics(
                update.node_id_candidates,
                self._matching_collections,
            ),
        }

    def _applied_update_sample(
        self,
        update: RuntimePropertyUpdate,
        params: Mapping[str, Any],
        matched_collections: Sequence[str],
    ) -> dict[str, Any]:
        """Return a redacted sample for one successfully routed update."""
        return {
            "node_id_hash": stable_digest(update.node_id),
            "node_type": update.node_type,
            "param_keys": safe_param_keys(params),
            "matched_collections": list(matched_collections),
        }

    def _matching_collections(self, node_id: int) -> list[str]:
        """Return loaded coordinator collections containing the node id."""
        matches: list[str] = []
        if node_id in self._devices:
            matches.append("devices")
        if node_id in self._gateways:
            matches.append("gateways")
        if node_id in self._data:
            matches.append("data")
        for name, collection in (
            ("groups", self._groups),
            ("rooms", self._rooms),
            ("areas", self._areas),
            ("houses", self._houses),
        ):
            if collection is not None and collection_contains_node(collection, node_id):
                matches.append(name)
        return matches


def _is_group_update(
    update: RuntimePropertyUpdate,
    loaded_payload: Mapping[str, Any] | None,
    matched_collections: Sequence[str],
) -> bool:
    """判断属性更新是否来自 LAN 灯组节点。"""
    if update.node_type == NODE_TYPE_GROUP:
        return True
    return loaded_payload is None and matched_collections == ["groups"]


def _topology_update_context(
    node_type: int | None,
    node_id: int,
    matched_collections: Sequence[str],
) -> RuntimeUpdateContext:
    """Return the HA listener context for one topology-node update."""
    if node_type == NODE_TYPE_ROOM:
        return ("room", str(node_id))
    if node_type == NODE_TYPE_AREA:
        return ("area", str(node_id))
    if node_type == NODE_TYPE_HOUSE:
        return ("house", str(node_id))
    if matched_collections == ["rooms"]:
        return ("room", str(node_id))
    if matched_collections == ["areas"]:
        return ("area", str(node_id))
    if matched_collections == ["houses"]:
        return ("house", str(node_id))
    return ("node", str(node_id))


__all__ = ["RuntimePropertyApplyMixin"]
