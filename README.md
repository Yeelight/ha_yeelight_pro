# Yeelight Pro

[English](README.md) | [中文](README_zh.md)

Yeelight Pro integration for Home Assistant. It supports Yeelight cloud and private deployment modes through one config flow.

## Current Status

- Integration status: pre-release hardening
- Verified tests: see [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- Default enabled platforms: 13 of 14 declared platforms
- Experimental platform: `vacuum`
- Not included as a platform: `text`
- Update model: cloud polling, with configurable interval
- HACS/community publication: not published from this workspace yet

## Features

- Cloud and private deployment setup
- Reauthentication flow for expired or invalid tokens
- Yeelight APP scan-login cloud setup through regional account APIs; QR-code login is the current primary cloud login UX
- Tested Yeelight OAuth token endpoint client helpers and a manual authorization-code setup path; full Home Assistant webhook/redirect OAuth login is not a current release target
- Configurable polling interval, debug mode, experimental platform loading, unknown capability filtering, manual non-destructive device import filtering, and topology Repairs notifications
- Canonical -> adapter -> converter -> projector -> entity architecture
- Lightweight Yeelight IoT spec registry for category, component, property, event, protocol, and `nodeType` facts
- Persistent Home Assistant `.storage` product schema cache for stable schema-aware projections across restarts
- Device registry topology for gateways and child devices
- Home Assistant diagnostics export with allowlisted config, IoT registry health, spec-correction counts, canonical spec runtime inventory, entity-candidate counts, and aggregate runtime health
- Non-destructive device/entity import filter preview in diagnostics, plus a conservative runtime gate that can stop future device-sourced entities from being added; it does not delete, disable, hide, or migrate existing entities or device registry entries
- Optional Home Assistant Repairs issue with sanitized add/remove/metadata-change counts when Yeelight device topology changes after setup
- Debug event service guarded by the `debug_mode` option
- Read-only manual refresh service that refreshes loaded coordinators and reconciles HA device/entity registries
- Real cloud device picker during cloud setup and later options changes: after
  a house is selected, the integration can load that house's device list and
  store selected device ids as an import filter for future device-sourced
  entities. If the device list cannot be loaded, users can continue without
  enabling or changing a device import filter.
- Opt-in analytics runtime with an admin-only manual refresh service and
  aggregate-only analytics sensors; it is disabled by default and does not store
  raw analytics payloads
- Registry cleanup service with dry-run and audit-id confirmation; confirmation
  disables stale entities through Home Assistant's registry and does not delete
  entity or device registry entries
- English and Simplified Chinese translations

## Supported Yeelight IoT Categories

These are Yeelight IoT categories, not Home Assistant entity platforms.

| Yeelight category | Default HA projection | Status |
| --- | --- | --- |
| `light` | `light` | Stable |
| `contact_sensor` | `binary_sensor` | Stable |
| `human_sensor` | `binary_sensor` | Stable |
| `light_sensor` | `sensor` | Stable |
| `curtain` | `cover` | Stable |
| `temp_control` | `climate` | Stable |
| `relay_switch` | `switch` | Stable |
| `scene_panel` | `event` + device triggers | Stable |
| `gateway` | Device registry topology | Stable |
| `knob_switch` | `event` + device triggers | Stable |
| `other` | Known sensor fallback only | Conservative |

`event`, `scene`, `button`, `select`, `number`, `vacuum`, and `text` are Home Assistant entity platforms or experimental projection targets. They are not Yeelight IoT device categories. `vacuum` is retained only as an opt-in experimental platform for future-compatible payloads.

See [docs/IOT_SPEC_REGISTRY.md](docs/IOT_SPEC_REGISTRY.md) for the registry boundary and [docs/HA_XIAOMI_HOME_GAP_REVIEW.md](docs/HA_XIAOMI_HOME_GAP_REVIEW.md) for the ha_xiaomi_home architecture comparison, borrowed ideas, and decision points.

## Installation

### Manual Installation

1. Run `python3 scripts/sync_local_ha_runtime.py --config-dir /path/to/homeassistant/config` to copy runtime files into your Home Assistant `custom_components` directory without tests or generated artifacts.
2. Restart Home Assistant.
3. Go to Settings -> Devices & services -> Add integration -> Yeelight Pro.

### HACS

This repository has HACS metadata and release packaging checks, but publication should only happen after local HA validation and release review are complete.

## Configuration

### Cloud Mode

1. Select Yeelight Pro cloud mode.
2. Select the Yeelight account region.
3. Use Yeelight APP 1.5.0 or later to scan the QR code shown by Home Assistant. Home Assistant will keep polling until the app grants the token or the five-minute QR code expires.
4. Select a house returned by the API.

Manual Access Token setup remains available as an advanced fallback.

### Private Deployment Mode

1. Select private deployment mode.
2. Enter the private server address.
3. Enter an Access Token and House ID.

## Options

Open the integration options to configure:

- Polling interval: 10-300 seconds, default 30 seconds
- Debug mode: enables `yeelight_pro.debug_emit_event`
- Experimental platforms: enables opt-in platforms such as `vacuum`
- Hide unknown entities: keeps unsupported capabilities from being exposed as generic entities
- Device import filtering: edit conservative manual rules or, for cloud
  entries, reopen the real device picker to adjust selected devices after setup
- Topology change Repairs: creates a Home Assistant Repairs issue with aggregate and sanitized diff counts when device/entity topology changes after setup; enabled by default

## Services

### `yeelight_pro.assign_areas`

Batch assign Home Assistant areas to Yeelight Pro devices.

### `yeelight_pro.auto_assign_areas`

Assign areas based on room keywords in device names.

### `yeelight_pro.debug_emit_event`

Emit a normalized Yeelight Pro runtime event for development and troubleshooting. This service requires `debug_mode` to be enabled in integration options.

### `yeelight_pro.refresh`

Refresh loaded Yeelight Pro data immediately and run device/entity registry reconciliation. Optional `entry_id` limits the refresh to one config entry.

## Development

```bash
cd extensions/ha_yeelight_pro
pytest -q
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases custom_components/yeelight_pro scripts hacs_publish.py
python3 validate_hacs.py
python3 scripts/check_release_zip.py
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
python3 scripts/verify_local_ha_soak.py
python3 scripts/verify_local_ha_recovery.py
```

Guarded production probes are available for authorized external validation and
must remain fail-closed without their explicit confirmation flags:

```bash
python3 scripts/verify_push_websocket.py
python3 scripts/verify_scan_login.py
python3 scripts/verify_cloud_devices.py
python3 scripts/verify_lan_gateway.py
python3 scripts/verify_analytics.py
```

CI/release entrypoints are kept in `.github/workflows/test.yaml`,
`.github/workflows/validate.yaml`, and `.github/workflows/release.yaml`.

Do not commit tokens, Home Assistant credentials, personal house IDs, or raw device data. Use sanitized fixtures for tests.

## Known Gaps

- Full Home Assistant webhook/redirect OAuth login is not implemented because
  Yeelight APP scan-login is the current cloud login path. If product direction
  reopens OAuth later, it will need Yeelight-issued credentials, redirect policy,
  CSRF state handling, and token lifecycle rules before implementation.
- Multi-region API hosts are implemented. Multiple cloud accounts are supported
  as separate config entries through scan-login account metadata, Open API
  clientId, or a redacted manual-token fingerprint. Multi-account-in-one-entry
  UX remains a roadmap item.
- Local gateway TCP control is available behind explicit options. When
  `local_gateway_control` is enabled and the host field is empty, the runtime
  attempts the documented UDP broadcast discovery once before opening TCP.
  mDNS, continuous network scanning, cloud/LAN topology merge, and hardware
  validation remain roadmap items.
- WebSocket push message builders, injected push manager, and opt-in live
  WebSocket runtime are covered by tests. The Yeelight event-notification
  material only documents WebSocket, so live event notifications are implemented
  only through WebSocket when `live_updates` is explicitly enabled. Default
  topology refresh and full-state fallback still use polling.
- Analytics runtime is implemented as explicit opt-in manual refresh and
  aggregate sensors only. Automatic polling, full historical analytics, raw
  payload persistence, and real production payload validation remain roadmap
  items.
- Full rules/spec filter engines remain roadmap items.
- Device import filtering currently supports diagnostics preview, manual
  comma-separated options rules, a real cloud device picker during cloud setup
  and later options changes, and conservative stop-new-entities behavior for
  future device-sourced entities. If the cloud device list cannot be loaded,
  setup can still create an entry and options can continue without changing the
  stored filter. Existing registry cleanup is available only as explicit dry-run plus
  audit-id confirmation that disables stale entities; delete, hide, migrate, and
  device-registry cleanup semantics remain roadmap items.

## License

MIT License
