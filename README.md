# Yeelight Pro

[English](README.md) | [中文](README_zh.md)

Yeelight Pro integration for Home Assistant. It supports Yeelight cloud,
private deployment, and LAN gateway connection modes through one config flow.

## Current Status

- Integration status: v1.0.4 release package is available
- Verified tests: see [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- Enabled Home Assistant platforms: 11
- Runtime platforms: `binary_sensor`, `button`, `climate`, `cover`, `event`,
  `fan`, `light`, `number`, `select`, `sensor`, and `switch`
- Update model: polling remains the default full-state refresh path, with a
  configurable interval
- HACS/community publication: HACS default repository PR
  [#8516](https://github.com/hacs/default/pull/8516) is under review

## Works with Home Assistant and Core Readiness

Yeelight is preparing selected Yeelight Pro devices or hubs for Works with Home
Assistant review. This repository is not a certification claim: HACS review,
Home Assistant Core upstreaming, Integration Quality Scale Gold, and Works with
Home Assistant approval are separate gates.

Planning and handover documents:

- [WWHA handover](docs/WORKS_WITH_HOME_ASSISTANT_HANDOVER.md)
- [WWHA application guide](docs/WORKS_WITH_HOME_ASSISTANT_APPLICATION_GUIDE.md)
- [Core and HACS migration strategy](docs/CORE_MIGRATION_STRATEGY.md)
- [Gold quality scale gap analysis](docs/QUALITY_SCALE_GOLD_GAP_ANALYSIS.md)
- [Local control model](docs/LOCAL_CONTROL.md)
- [Supported devices template](docs/SUPPORTED_DEVICES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Automation examples](docs/AUTOMATION_EXAMPLES.md)

## Features

- Cloud, private deployment, and LAN gateway setup
- Reauthentication flow for expired or invalid tokens
- Yeelight APP scan-login cloud setup through regional account APIs; QR-code login is the current primary cloud login UX
- Configurable polling interval, debug mode, unknown capability filtering,
  manual non-destructive device import filtering, and topology Repairs
  notifications
- Cloud event notifications use the explicit `live_updates` WebSocket runtime;
  private deployment entries use the same runtime with an optional private push
  URL; polling remains the default full-state refresh path
- LAN gateway runtime behind the LAN connection mode and `local_gateway_control`
  option
- Canonical -> adapter -> converter -> projector -> entity architecture
- Lightweight Yeelight IoT spec registry for category, component, property, event, protocol, and `nodeType` facts
- Persistent Home Assistant `.storage` product schema cache for stable schema-aware projections across restarts
- Device registry topology for gateways and child devices
- House-level analytics diagnostic sensors for alarm, energy, user-action, and
  endpoint-health aggregates; optional analytics endpoint failures degrade to
  unavailable diagnostic values instead of blocking setup
- Home Assistant diagnostics export with allowlisted config, IoT registry health, spec-correction counts, canonical spec runtime inventory, entity-candidate counts, and aggregate runtime health
- Non-destructive device/entity import filter preview in diagnostics, plus a conservative runtime gate that applies the selected import scope before new device-sourced entities are submitted
- Optional Home Assistant Repairs issue with sanitized add/remove/metadata-change counts when Yeelight device topology changes after setup
- Debug event service guarded by the `debug_mode` option
- Read-only manual refresh service that refreshes loaded coordinators and reconciles HA device/entity registries
- Real cloud device picker during cloud setup and later options changes: after
  a house is selected, the integration can load that house's device list and
  store selected device ids as an import filter for new device-sourced
  entities. If the device list cannot be loaded, users can continue without
  enabling or changing a device import filter.
- Registry cleanup service with dry-run and audit-id confirmation; confirmation
  disables stale entities through Home Assistant's registry
- English and Simplified Chinese translations

## Supported Yeelight IoT Categories

The table lists Yeelight IoT categories and their current Home Assistant projections.

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

Cloud scenes are exposed as `button` entities that call Yeelight scene execution.

See [docs/IOT_SPEC_REGISTRY.md](docs/IOT_SPEC_REGISTRY.md) for the registry boundary and release mapping contract.

## Installation

### Manual Installation

1. Run `python3 scripts/sync_local_ha_runtime.py --config-dir /path/to/homeassistant/config` to copy runtime files into your Home Assistant `custom_components` directory without tests or generated artifacts.
2. Restart Home Assistant.
3. Go to Settings -> Devices & services -> Add integration -> Yeelight Pro.

### HACS

The GitHub release `v1.0.4` contains the HACS zip asset
`yeelight_pro.zip`. HACS default repository PR
[#8516](https://github.com/hacs/default/pull/8516) is still under review; until
that PR is merged, install this repository as a custom HACS integration
repository.

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
- Hide unknown entities: keeps unmapped or low-confidence capabilities from being exposed as generic entities
- Device import filtering: edit conservative manual rules or, for cloud
  entries, reopen the real device picker to adjust selected devices after setup
- Live updates: cloud/private entries can enable the WebSocket runtime
- Private push URL: private entries can override the WebSocket push endpoint
- Local gateway control: LAN entries can configure gateway host and port
- Topology change Repairs: creates a Home Assistant Repairs issue with aggregate and sanitized diff counts when device/entity topology changes after setup; enabled by default

## Services

### `yeelight_pro.assign_areas`

Batch assign Home Assistant areas to Yeelight Pro devices.

### `yeelight_pro.auto_assign_areas`

Assign areas based on room keywords in device names.

### `yeelight_pro.debug_emit_event`

Emit a normalized Yeelight Pro runtime event for development and troubleshooting. This service requires `debug_mode` to be enabled in integration options.

### `yeelight_pro.debug_dump_push_health`

Write aggregate WebSocket push health to the Home Assistant log for
development and troubleshooting. This service requires `debug_mode` to be
enabled.

### `yeelight_pro.debug_emit_push_payload`

Inject a synthetic property push payload into the runtime bridge. This service
requires `debug_mode` to be enabled and does not control a real device.

### `yeelight_pro.refresh`

Refresh loaded Yeelight Pro data immediately and run device/entity registry reconciliation. Optional `entry_id` limits the refresh to one config entry.
Optional `refresh_product_schemas` refreshes product schemas and falls back to
cached schemas if the refresh fails.

### `yeelight_pro.cleanup_registry`

Run a dry-run stale entity registry cleanup preview. Confirmation requires the
same `entry_id` and returned `audit_id`; confirmed cleanup disables stale
entities through Home Assistant's entity registry.

## Development

```bash
cd extensions/ha_yeelight_pro
pytest -q
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases --exclude custom_components/yeelight_pro/tests custom_components/yeelight_pro scripts hacs_publish.py
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
```

CI/release entrypoints are kept in `.github/workflows/test.yaml`,
`.github/workflows/validate.yaml`, and `.github/workflows/release.yaml`.

Do not commit tokens, Home Assistant credentials, personal house IDs, or raw device data. Use sanitized fixtures for tests.

## Runtime Model

- Region and account isolation is entry based: each cloud account, region, and
  house combination creates its own Home Assistant config entry.
- Cloud event notifications use the explicit `live_updates` WebSocket runtime.
  Private deployment entries use the same runtime with an optional private push
  URL. Polling remains the default full-state refresh path.
- LAN gateway control is available through LAN-mode entries. When
  `local_gateway_control` is enabled and no host is configured, the runtime
  performs one documented UDP discovery attempt before opening the TCP gateway
  session.
- Device import filtering combines diagnostics preview, manual option rules,
  setup/options real device picker selections, and a conservative gate before
  new device-sourced entities are submitted.
- Existing registry cleanup is exposed as an explicit dry-run plus audit-id
  confirmation service that disables stale entities through Home Assistant's
  registry.

## License

MIT License
