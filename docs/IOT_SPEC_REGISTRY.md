# Yeelight IoT Spec Registry

## Scope

`custom_components/yeelight_pro/capabilities/` now contains a lightweight Yeelight IoT spec registry. It is a code-level fact source for the current Home Assistant projection layer:

- IoT categories and their first HA platform projection.
- Core components and platform hints.
- Core property semantics used by HA entities.
- Event aliases normalized to stable snake_case event types.
- Connection protocol metadata.
- Open platform `nodeType` constants.
- Component property key helpers for `{componentIndex}-{propName}`.

The registry is intentionally static for this release hardening pass. Runtime CSV parsing is not used because the integration package should not depend on local research files under `docs/iot`.

Yeelight does not use MIoT URNs, SIID, PIID, AIID, or EIID. The registry therefore models Yeelight-specific fields: category, component alias/id, property abbreviation, event text/id, connection protocol, `nodeType`, and component property keys.

## Current Capability Boundary

The registry includes the 11 Yeelight IoT categories found in local IoT materials:

`light`, `contact_sensor`, `human_sensor`, `light_sensor`, `curtain`, `temp_control`, `relay_switch`, `scene_panel`, `other`, `gateway`, and `knob_switch`.

Cloud scenes are executable remote actions and are exposed as Home Assistant `button` entities.

Connection protocols such as Mesh, DALI, Matter, and Thread are stored as product or bridge metadata. They do not imply local control support.

## Home Assistant Platform Mapping Contract

The first release maps Yeelight payloads by IoT category plus documented
property/event evidence. A broad cloud `category` or `type` value such as
`light` is not enough to project a device as a Home Assistant `light`.

Supported platforms:

| HA platform | Evidence boundary |
| --- | --- |
| `light` | Yeelight light category/components with `p`/`l`/`ct`/`c` light properties |
| `binary_sensor` | Read-only boolean state such as `mv`, `dc`, `alm`, battery charge flags |
| `sensor` | Read-only scalar telemetry such as `t`, `h`, `luminance`, `bl`, `curp`, `iec` |
| `event` | Product-schema or OpenAPI/WebSocket event declarations |
| `cover` | Curtain position properties such as `cp` and writable `tp` |
| `climate` | Temperature-control properties such as `acp`, `acm`, `actt`, `acct`, `acf`, `rfh*` |
| `switch` | Relay-switch `p`/`sp` properties and indexed switch components |
| `button` | Documented cloud scene execution only |
| `select` / `number` | House topology selectors and group `l`/`ct` helpers |

Open platform `nodeType` values are represented for control path clarity:

| Node | nodeType |
| --- | --- |
| room | 1 |
| device | 2 |
| area | 3 |
| group | 4 |
| house | 5 |

The component property key helper follows the Yeelight IoT model:

- `format_component_property_key(None, "p") -> "p"`
- `format_component_property_key(1, "p") -> "1-p"`
- `parse_component_property_key("1-p") -> component index `1`, property `p`

Open API property control/read helpers model the documented path and body
contracts at the client boundary:

- House/project snapshot:
  `/v1/open/node/house/{houseId}/r/info`.
- Single-node single-property control:
  `/v1/open/control/house/{houseId}/control/{nodeType}/{resId}/w/properties/{propName}`.
- Single-node multi-property control:
  `/v1/open/control/house/{houseId}/control/{nodeType}/{resId}/w/properties`.
- Multi-node single-property control:
  `/v1/open/control/house/{houseId}/control/{nodeType}/w/properties/{propName}`.
- Single-node and multi-node property reads use the matching `/r/properties`
  forms.

These helpers are low-level contracts that keep cloud read/write path shape
centralized before Home Assistant entities or services consume them.

## Product Schema Cache Boundary

The integration now persists product schemas in Home Assistant `.storage` through `yeelight_pro.product_schemas`.

The cache stores product schema documents keyed by PID only. It must not store user tokens, account data, house IDs, device IDs, MAC addresses, room names, runtime state, or raw device payloads.

## Product Schema Correction Boundary

`custom_components/yeelight_pro/capabilities/spec_correction.py` contains the first Yeelight-specific schema correction layer.

It currently supports conservative filter/modify behavior only:

- Normalize property `format` values such as `bool` to `boolean`.
- Derive internal property access from Yeelight `operators`, while preserving known read-only legacy access.
- Mark global/config/info properties as runtime-filtered so they do not become normal entity state.
- Mark sensitive or credential-like properties such as `localToken`, `hrbk`, and `deviceKey` as runtime-filtered even when upstream schema hints are incomplete.
- Keep `valueRange` data as reported by the upstream schema; missing `step` remains `None`.

Diagnostics only expose aggregate correction counts. They must not include raw schema documents, PID/device/house identifiers, credential-like property values, or original payloads.

The correction layer keeps schema normalization separate from WebSocket runtime
and local gateway behavior. WebSocket send-side message builders, the injected
push manager, and the opt-in WebSocket runtime are tested separately. Device
and entity import filtering has diagnostics-safe aggregate preview plus a
conservative runtime gate that applies the selected import scope before new
device-sourced entities are submitted.

## Entity Candidate And Filter Preview Boundary

`custom_components/yeelight_pro/entity_candidates.py` centralizes projected entity candidates before Home Assistant platform entities are built, keeping lifecycle decisions tied to the final Yeelight-specific projection set.

Diagnostics expose:

- `runtime.spec_runtime_inventory`: aggregate canonical `ha_product_model` inventory counts for product models, components, properties, events, event params, component actions, device actions, action params, readable properties, and writable properties.
- `runtime.entity_candidates`: aggregate candidate counts by platform, source, source class, duplicate registry key count, and availability.
- `runtime.device_import_filter_preview`: aggregate device counts if the stored import filter were applied, plus `rules_by_dimension`, `ignored_rule_count`, and `distinct_value_counts_by_dimension`.
- `runtime.entity_import_filter_preview`: aggregate entity candidate counts after the same device filter preview, using the same source-class and duplicate-key quality counters.

The runtime inventory counts canonical product model buckets only. It does not expose product model ids, component ids, property ids, event ids, action names, runtime state, or raw schema fields. It is intentionally separate from `spec_correction`, which summarizes raw upstream schema corrections.

The filter preview accepts Yeelight field aliases such as `category`, `nodeType`, `roomId`, `gatewayDeviceId`, `productId`, and `deviceId`, then normalizes them to canonical dimensions: `categories`, `types`, `rooms`, `gateways`, `product_ids`, and `devices`. Only those canonical dimensions affect filtering; raw rule values are never exported.

The previews do not expose `unique_id`, `device_id`, house/room/gateway identifiers, scene/group ids, raw filter rules, or raw device payloads. Runtime filtering stops new device-sourced entities when HA entity registry confirms the candidate is new. Options expose a conservative manual rule editor for Yeelight dimensions using comma-separated values. Cloud setup and cloud entry options also include a real device picker: after the selected house is available, the integration calls the documented device list client path and stores selected device ids as an import filter. If the device list cannot be loaded during setup, the entry can still be created with device import filtering disabled; if it cannot be loaded from options, the existing filter is not overwritten. Existing stale-entity cleanup is available through the explicit `cleanup_registry` service: dry-run returns an audit id, confirm requires that audit id and disables stale entities through Home Assistant's registry.

Visible device-import filter form keys are also treated as diagnostics
redaction keys. This is defensive: those keys should normally be collapsed into
the stored `device_import_filter` structure before persistence, but diagnostics
must still redact selected room, gateway, product, or device identifiers if a
form-only key ever appears in entry options.

## Live WebSocket Runtime

The open platform event-notification material documents WebSocket, subscribe,
and heartbeat behavior. The integration contains an explicit opt-in WebSocket
runtime:

- `push_contract.py` builds the documented WebSocket URL, subscribe frame,
  heartbeat frame, heartbeat timeout, and reconnect-delay policy helpers.
- `push_transport.py` opens the WebSocket through Home Assistant's aiohttp
  session, sends the subscribe frame, starts a reader task, and sends
  heartbeat frames.
- `live_runtime.py` starts the transport only when `live_updates=true` in
  config-entry options.
- Cloud event notifications use the WebSocket runtime. Polling remains the
  default topology refresh and full-state refresh path.
- Received `prop` and `event` payloads are dispatched to the coordinator.
  Subscribe and heartbeat ACK control frames are ignored for payload accounting;
  failed control frames close the current websocket through the aggregate-only
  `PushControlFrameError` boundary.
- Dispatched `prop` and `event` payloads are normalized through the shared
  coordinator runtime bridge, so entity state and HA event dispatch use the
  same path as already decoded push/LAN payload tests.
- Unload and optional-runtime startup failure paths stop the push manager.
- `scripts/verify_push_websocket.py` is a source-only production probe harness.
  It is no-network by default, reads token material only from the
  `YEELIGHT_PRO_PUSH_TOKEN` environment variable, requires the explicit
  `--confirm-production-websocket` flag, and reports only aggregate redacted
  frame counts, control/data classifications, JSON field-shape keys, and error
  class names.

The default update model remains polling. The WebSocket runtime stays behind
the explicit `live_updates` option and has no-network coverage for ACK/error
control-frame handling plus a guarded production probe entrypoint.

## LAN Local Protocol Runtime Boundary

The local Yeelight Pro gateway document is represented by protocol helpers and
an explicit opt-in TCP runtime. `lan_contract.py` covers:

- UDP discovery constants: broadcast text, discovery port, and TCP gateway
  port.
- Discovery response parsing for the documented `pid/mac/did/ip` text shape.
- JSON frame encoding and decoding with the documented `\r\n` separator.
- Request frame builders for `gateway_get.*` and `gateway_set.prop`.
- Identification of gateway-to-client `gateway_post.*` push frames.

`lan_runtime.py` opens a TCP connection only when `local_gateway_control=true`.
If the option is enabled and no gateway host is configured, it performs one
documented UDP broadcast discovery attempt and uses the first valid
`pid/mac/did/ip` response as the TCP host. It requests `gateway_get.topology`,
can send documented `gateway_set.prop` frames, and dispatches received
CRLF-delimited `gateway_post.*` frames through the coordinator runtime bridge.
Diagnostics may report `lan_discovery_parser=true`, `lan_message_contract=true`,
`lan_payload_adapter=true`, `runtime_payload_bridge=true`, `lan_control=true`,
and `local_gateway_control=true`; runtime health still reports only aggregate
state and counters, never host, token, MAC, or device identifiers.
