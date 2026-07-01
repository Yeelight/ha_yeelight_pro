# Yeelight Pro

[English](README.md) | [中文](README_zh.md)

Yeelight Pro is a Home Assistant custom integration for Yeelight Pro homes,
devices, gateways, scenes, and runtime diagnostics. It supports Yeelight cloud,
private deployment, and LAN gateway connection modes through one config flow.

## Current Status

- Current release: `v1.0.5`, with the HACS zip asset `yeelight_pro.zip`
- HACS default repository PR:
  [#8516](https://github.com/hacs/default/pull/8516), under review
- Early access path: add this repository to HACS as a custom integration
  repository
- Minimum HACS metadata target: HACS `2.0.0`, Home Assistant `2024.1.0`
- Verified tests and release gates: see
  [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- Enabled Home Assistant platforms: 11
- Runtime platforms: `binary_sensor`, `button`, `climate`, `cover`, `event`,
  `fan`, `light`, `number`, `select`, `sensor`, and `switch`
- Update model: Polling remains the default full-state refresh path, with a
  configurable interval. Cloud and private event notifications use the explicit
  `live_updates` WebSocket runtime.

## Features

- Cloud, private deployment, and LAN gateway setup in one config flow
- Yeelight APP scan-login setup through regional account APIs; QR-code login is
  the primary cloud login UX
- Advanced manual access-token setup for existing Yeelight Pro deployments
- Reauthentication flow for expired or invalid tokens
- Configurable polling interval, debug mode, unknown capability filtering,
  manual non-destructive device import filtering, live updates, LAN gateway
  control, and topology Repairs notifications
- Product schema loading from both v1 and v2 schema endpoints, merged
  conservatively for maximum capability coverage
- Persistent Home Assistant `.storage` product schema cache for stable
  schema-aware projections across restarts
- Canonical -> adapter -> converter -> projector -> entity architecture
- Lightweight Yeelight IoT registry for category, component, property, event,
  protocol, and `nodeType` facts
- Device registry topology for gateways, child devices, scenes, groups, rooms,
  areas, and house-level helper entities
- House-level analytics diagnostic sensors for alarm, energy, user-action, and
  endpoint-health aggregates; optional analytics endpoint failures degrade to
  unavailable diagnostic values instead of blocking setup
- Home Assistant diagnostics export with allowlisted config, IoT registry
  health, spec-correction counts, canonical spec runtime inventory,
  entity-candidate counts, device-import preview, and aggregate runtime health
- Non-destructive device/entity import filtering: selected devices or manual
  rules only gate new device-sourced entity submissions, and do not delete,
  hide, migrate, or disable existing registry entries
- Real cloud device picker during setup and later options changes. If the
  device list cannot be loaded, setup can continue without enabling a filter
  and options keep the existing filter unchanged.
- Registry cleanup service with dry-run and audit-id confirmation; confirmed
  cleanup disables stale entities through Home Assistant's entity registry
- Debug services guarded by the `debug_mode` option
- Read-only manual refresh service that refreshes loaded coordinators and
  reconciles Home Assistant device/entity registries
- English and Simplified Chinese translations

## Installation

### HACS Installation

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Yeelight&repository=ha_yeelight_pro&category=integration)

Use this path while HACS default repository PR
[#8516](https://github.com/hacs/default/pull/8516) is still under review.
The flow follows HACS' custom repository model: add a repository URL, choose
the correct repository type, then download the integration from HACS.

Requirements:

- Home Assistant `2024.1.0` or later
- HACS `2.0.0` or later
- A Home Assistant backup before installing any custom integration

Quick path:

1. Click the **Open your Home Assistant instance and add this repository to
   HACS** button above.
2. Confirm the repository in Home Assistant.
3. Make sure the category is **Integration**.
4. Install **Yeelight Pro** from HACS.
5. Restart Home Assistant.
6. Go to **Settings -> Devices & services -> Add integration**.
7. Search for **Yeelight Pro** and start configuration.

Manual custom repository path:

1. Open Home Assistant.
2. Go to **HACS**.
3. Click the three-dot menu in the upper-right corner.
4. Select **Custom repositories**.
5. In **Repository**, enter:

   ```text
   https://github.com/Yeelight/ha_yeelight_pro
   ```

6. In **Type**, select **Integration**.
7. Click **Add**.
8. Search for **Yeelight Pro** in HACS.
9. Open the repository page and click **Download**. Choose the latest release
   if HACS asks for a version.
10. Restart Home Assistant.
11. Go to **Settings -> Devices & services -> Add integration**.
12. Search for **Yeelight Pro** and start configuration.

If the integration does not appear after restart, refresh the browser cache and
check that HACS installed it under your Home Assistant configuration directory
as `custom_components/yeelight_pro/`.

Useful references:

- HACS custom repositories:
  <https://www.hacs.xyz/docs/faq/custom_repositories/>
- HACS integration repositories:
  <https://www.hacs.xyz/docs/use/repositories/type/integration/>

### Manual Development Installation

This path is for local development or QA, not for ordinary HACS users.

```bash
python3 scripts/sync_local_ha_runtime.py --config-dir /path/to/homeassistant/config
```

Then restart Home Assistant and go to
**Settings -> Devices & services -> Add integration -> Yeelight Pro**.

Do not copy the whole source directory into Home Assistant. The sync script
copies runtime files only and excludes tests, caches, and generated artifacts.

## Configuration

### Cloud Mode

1. Select Yeelight Pro cloud mode.
2. Select the Yeelight account region: CN, SG, US, or DE.
3. Use Yeelight APP 1.5.0 or later to scan the QR code shown by Home
   Assistant. Home Assistant keeps polling until the app grants the token or
   the five-minute QR code expires.
4. Select a house returned by the API.
5. Optionally adjust the device picker before finishing setup.

Manual Access Token setup remains available as an advanced fallback.

### Private Deployment Mode

1. Select private deployment mode.
2. Enter the private server address.
3. Enter an Access Token and House ID.
4. Optionally configure a private WebSocket push URL in options.

### LAN Gateway Mode

1. Select LAN gateway mode.
2. Enter gateway host, port, and product id when known.
3. If `local_gateway_control` is enabled later and no host is configured, the
   runtime performs one documented UDP discovery attempt before opening the TCP
   gateway session.

## Supported Yeelight IoT Categories

The table lists Yeelight IoT categories and their current Home Assistant
projections. A category row means the integration has a projection strategy for
that category; it does not mean every SKU exposes every manufacturer-app
feature in Home Assistant.

| Yeelight category | Default HA projection | Status |
| --- | --- | --- |
| `light` | `light` | Stable |
| `contact_sensor` | `binary_sensor` + event/device trigger when schema events exist | Stable |
| `human_sensor` | `binary_sensor` + event/device trigger when schema events exist | Stable |
| `light_sensor` | `sensor` | Stable |
| `curtain` | `cover` | Stable |
| `temp_control` | `climate` | Stable |
| `relay_switch` | `switch` | Stable |
| `scene_panel` | `event` + device trigger | Stable |
| `gateway` | Device registry topology and diagnostics | Stable |
| `knob_switch` | `event` + device trigger | Stable |
| `other` | Known read-only sensor fallback only | Conservative |

Cloud scenes are exposed as `button` entities that call Yeelight scene
execution.

See [docs/IOT_SPEC_REGISTRY.md](docs/IOT_SPEC_REGISTRY.md) for the registry
boundary and release mapping contract.

## Options

Open the integration options to configure:

- Polling interval: 10-300 seconds, default 30 seconds
- Debug mode: enables guarded debug services
- Hide unknown entities: keeps unmapped or low-confidence capabilities from
  being exposed as generic entities
- Device import filtering: edit conservative manual rules, or for cloud
  entries reopen the real device picker to adjust selected devices after setup
- Live updates: cloud/private entries use the explicit `live_updates`
  WebSocket runtime. Polling remains the default full-state refresh path.
- Private push URL: private entries can override the WebSocket push endpoint
- Local gateway control: LAN entries can configure gateway host and port
- Topology change Repairs: creates a Home Assistant Repairs issue with
  aggregate and sanitized diff counts when device/entity topology changes after
  setup; enabled by default

## Services

### `yeelight_pro.assign_areas`

Batch assign Home Assistant areas to Yeelight Pro devices.

### `yeelight_pro.auto_assign_areas`

Assign areas based on room keywords in device names.

### `yeelight_pro.debug_emit_event`

Emit a normalized Yeelight Pro runtime event for development and
troubleshooting. This service requires `debug_mode` to be enabled in
integration options.

### `yeelight_pro.debug_dump_push_health`

Write aggregate WebSocket push health to the Home Assistant debug log for
development and troubleshooting. This service requires `debug_mode` to be
enabled.

### `yeelight_pro.debug_emit_push_payload`

Inject a synthetic property push payload into the runtime bridge. This service
requires `debug_mode` to be enabled and does not control a real device.

### `yeelight_pro.refresh`

Refresh loaded Yeelight Pro data immediately and run device/entity registry
reconciliation. Optional `entry_id` limits the refresh to one config entry.
Optional `refresh_product_schemas` refreshes product schemas and falls back to
cached schemas if the refresh fails.

### `yeelight_pro.cleanup_registry`

Run a dry-run stale entity registry cleanup preview. Confirmation requires the
same `entry_id` and returned `audit_id`; confirmed cleanup disables stale
entities through Home Assistant's entity registry.

## Runtime Model

- Region and account isolation is entry based: each cloud account, region, and
  house combination creates its own Home Assistant config entry.
- Product schema completeness is prioritized by reading and merging both v1 and
  v2 schema responses when available.
- Cloud event notifications use the explicit `live_updates` WebSocket runtime.
  Private deployment entries use the same runtime with an optional private push
  URL. Polling remains the default full-state refresh path.
- LAN gateway control is available through LAN-mode entries and is controlled
  by the `local_gateway_control` option.
- Device import filtering combines diagnostics preview, manual option rules,
  setup/options real device picker selections, and a conservative gate before
  new device-sourced entities are submitted.
- Registry cleanup is exposed as an explicit dry-run plus audit-id confirmation
  service that disables stale entities through Home Assistant's registry.

## Known Boundaries

- This integration does not expose unsupported or unknown writable capabilities
  as generic switches, selects, numbers, text entities, or buttons.
- Unknown scalar properties may only become conservative read-only sensors when
  the relevant option allows them.
- Device import filtering does not clean, remove, disable, hide, or migrate
  existing entities or devices.
- Debug services are disabled unless `debug_mode` is enabled.
- Guarded production probes require explicit confirmation flags and must remain
  fail-closed without them.

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

Do not commit tokens, Home Assistant credentials, personal house IDs, or raw
device data. Use sanitized fixtures for tests.

## License

MIT License
