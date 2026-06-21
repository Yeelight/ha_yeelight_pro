# Changelog

All notable changes to the Yeelight Pro integration will be documented in this file.

## [Unreleased]

### Documentation

- Updated README, release, installation, and verification docs to match the
  current v1.0.4 package, HACS PR status, enabled platform set, runtime
  boundaries, and registered services.

## [1.0.4] - 2026-06-21

### Fixed

- Maximized private-deployment product schema coverage by merging v1 and v2
  schema responses before projecting Home Assistant entities.
- Added full-sample private-house audit coverage for controls, diagnostics,
  sensors, events, topology nodes, and push payload matching.
- Fixed Home Assistant hassfest translation validation by moving private URL
  examples into config-flow description placeholders.

## [1.0.2] - 2026-06-15

### Fixed

- Added bundled HACS brand icon assets so validation no longer falls back to the Home Assistant brands repository.
- Stabilized the GitHub Actions test gate on Python 3.11, matching the release and validation workflows used for HACS publication.
- Fixed write APIs that referenced an implicit `client.house_id`; control, toggle, scene, and group commands now receive `house_id` explicitly.
- Preserved authentication failures as `ConfigEntryAuthFailed` so Home Assistant can trigger reauthentication.
- Made `pytest -q` reproducible from the integration root through local `pyproject.toml` settings.
- Aligned the runtime platform set, release package, and documentation around the current Home Assistant projection surface.
- Fixed entity-registry reconciliation so cloud scene buttons stay active while removed native `scene.*` entities are treated as stale cleanup candidates.
- Refreshed integration-owned entity registry metadata for active entities, including friendly multi-key switch names and cloud-scene button icons, without overwriting user custom names.
- Connected official Yeelight product schemas to the coordinator's canonical product and runtime device-instance payloads, so projector layers consume the same schema-aware path in production and tests.
- Hardened diagnostics redaction for device-import filter form-only fields so room, gateway, product, and device identifiers cannot leak if those fields reach diagnostics.
- Rejected malformed WebSocket push node lists consistently for both `prop` and `event` payload adapters instead of partially swallowing bad frames.
- Preserved and sent the documented Open API `clientId` header when scan-login or migrated account metadata provides a non-secret client id, while keeping the manual access-token path compatible.

### Added

- Options flow for polling interval, debug mode, unknown capability handling, live updates, local gateway control, manual non-destructive device import filtering, and topology Repairs notifications.
- Runtime platform filtering keeps the loaded Home Assistant platform set aligned with documented Yeelight capabilities.
- Lightweight capability registries for IoT category mapping, property semantics, and event aliases.
- Persistent Home Assistant `.storage` product schema cache so temporary schema endpoint failures or Home Assistant restarts do not immediately degrade canonical device projections.
- Home Assistant diagnostics export with sensitive config redaction and aggregate runtime counts.
- Diagnostics aggregates for IoT registry health, spec correction, projected entity candidates, option/runtime alignment, and non-destructive device/entity import filter previews.
- No-network Yeelight WebSocket received-payload adapters for documented `prop` and `event` payloads, routed through the shared runtime state/event bridge.
- Optional Home Assistant Repairs issue for post-setup Yeelight device topology changes, enabled by default and controlled from integration options.
- Read-only manual refresh service with registry reconciliation and no new write path.
- Simplified Chinese translation file aligned with `strings.json` and `en.json`.
- P0 regression tests for control URLs, auth lifecycle, platform imports, options, capability mapping, translations, and Yeelight IoT category projection.
- Release package structure checker at `scripts/check_release_zip.py`.
- Release preflight guards for diagnostics capability flags and the non-destructive dynamic entity filter runtime contract.

### Changed

- Documentation now separates Yeelight IoT device categories from Home Assistant entity platforms.
- Debug event emission now requires `debug_mode` and normalizes backend event aliases.
- Debug event service registration now lives in `debug_service.py` to keep the integration entrypoint focused.
- Gateway category is documented as device-registry topology rather than a normal control entity.

### Current Verification

- `python3 -m compileall -q custom_components/yeelight_pro`
- `pytest -q`
- `ruff check custom_components/yeelight_pro`
- `mypy --explicit-package-bases --ignore-missing-imports custom_components/yeelight_pro`
- `python3 validate_hacs.py`
- `python3 scripts/check_release_zip.py`

Use the latest local command output as the source of truth. This changelog intentionally does not freeze historical test counts, coverage percentages, or release zip file counts.

### Runtime Model

- Cloud accounts, regions, and houses are isolated through separate config entries.
- Cloud event notifications use the explicit `live_updates` WebSocket runtime.
- Local gateway control uses the explicit `local_gateway_control` LAN runtime,
  including one UDP discovery fallback when the option is enabled and no host is
  configured.
- Device import filtering uses diagnostics preview, manual option rules,
  setup/options real device picker selections, and the conservative new-entity
  gate.

## [0.1.0] - 2026-06-03

### Added

- Initial migration from `lucore_gateway` into the `yeelight_pro` custom integration layout.
- Canonical, adapter, converter, projector, coordinator, client, and platform entity layers.
- Cloud and private deployment configuration flow foundation.

### Notes

- Earlier generated reports overstated release readiness and platform coverage. Use this changelog and README files as the current release-facing source of truth.
