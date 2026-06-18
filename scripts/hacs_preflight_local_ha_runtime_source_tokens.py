"""Additional runtime component source contract tokens."""

from __future__ import annotations

LOCAL_HA_RUNTIME_ADDITIONAL_SOURCE_TOKENS = {
    "custom_components/yeelight_pro/config_flow_private.py": {
        "PrivateConfigFlowMixin": "private deployment config-flow split mixin",
        "CONF_PRIVATE_PUSH_DOMAIN": "private deployment independent push endpoint field",
        "deployment_push_base_url": "private deployment push URL normalization",
        "async_step_cloud_auth_method": "shared cloud/private auth flow handoff",
    },
    "custom_components/yeelight_pro/config_flow_entry_data.py": {
        "build_cloud_entry_data": "config-flow entry data helper split",
        "CONF_PRIVATE_PUSH_DOMAIN": "private push field persisted in entry data",
    },
    "custom_components/yeelight_pro/const.py": {
        "CLOUD_REGION_PUSH_BASE_URLS": "regional WebSocket push endpoint map",
        "push-sg.yeelight.com": "Singapore WebSocket push endpoint",
        "push-us.yeelight.com": "US WebSocket push endpoint",
        "push-de.yeelight.com": "EU WebSocket push endpoint",
        "CONF_PRIVATE_PUSH_DOMAIN": "private deployment independent push endpoint key",
    },
    "custom_components/yeelight_pro/deployment_urls.py": {
        "deployment_root_url": "private deployment root URL normalizer",
        "deployment_iot_base_url": "private deployment IoT API derivation",
        "deployment_account_base_url": "private deployment Account API derivation",
        "deployment_push_base_url": "private deployment WebSocket push derivation",
        "api-test.yeedev.com": "private test API host push endpoint override",
        "ws-test.yeedev.com": "private test WebSocket endpoint override",
        "/apis/iot": "legacy IoT API prefix compatibility",
        "/apis/account": "Account API endpoint suffix",
        "/ws": "WebSocket push endpoint suffix",
    },
    "custom_components/yeelight_pro/config_flow_options.py": {
        "CONF_PRIVATE_PUSH_DOMAIN": "private deployment push field in options schema",
        "merge_private_entry_data": "private push endpoint data merge helper",
        "visible_entry_data_change_count": "private data changes are counted in options flow",
        "deployment_push_base_url": "private push options input normalization",
    },
    "custom_components/yeelight_pro/options_flow.py": {
        "_pending_entry_data": "options flow carries config-entry data changes",
        "async_update_entry": "options flow updates config-entry data",
        "visible_entry_data_change_count": "private data changes are counted in confirmation",
    },
    "custom_components/yeelight_pro/live_runtime.py": {
        "CLOUD_REGION_PUSH_BASE_URLS": "regional cloud WebSocket push endpoint selection",
        "CONF_PRIVATE_PUSH_DOMAIN": "private deployment independent push endpoint key",
        "enable_ip_fallback": "private fake-ip DNS fallback runtime gate",
    },
    "custom_components/yeelight_pro/push_transport_dns.py": {
        "FAKE_IP_NETWORKS": "fake-ip DNS range allowlist",
        "198.18.0.0/15": "Clash fake-ip CIDR boundary",
        "websocket_ip_fallback": "fake-ip DNS fallback helper",
        "resolve_host_ips": "local resolver fake-ip detection",
        "resolve_public_dns_ips": "public DNS fallback resolver",
        "server_hostname": "TLS SNI preservation for direct-IP fallback",
        '"Host"': "original Host header preservation",
    },
    "custom_components/yeelight_pro/push_transport_connection.py": {
        "PushTransportConnectionMixin": "WebSocket connection helper split",
        "websocket_ip_fallback": "fake-ip fallback helper use",
        "enable_ip_fallback": "fake-ip fallback runtime gate",
        "ws_connect": "WebSocket connect boundary",
    },
    "custom_components/yeelight_pro/push_transport_runtime.py": {
        "PushTransportRuntimeMixin": "WebSocket reader helper split",
        "json_payload_from_message": "incoming JSON object filter",
        "_cleanup_after_reader_exit": "reader cleanup boundary",
        "abnormal_close_before_first_frame": "early close diagnostics reason",
    },
    "custom_components/yeelight_pro/push_transport_reconnect.py": {
        "PushTransportReconnectMixin": "WebSocket reconnect helper split",
        "_schedule_reconnect": "automatic reconnect scheduler",
        "_reconnect_until_connected": "automatic reconnect loop",
    },
    "custom_components/yeelight_pro/entry_migration_helpers.py": {
        "coerce_int": "entry migration integer coercion helper",
        "coerce_bool": "entry migration boolean coercion helper",
        "first_value": "legacy field alias helper",
    },
    "custom_components/yeelight_pro/diagnostic_runtime.py": {
        "push_manager_health": "push manager nested transport health diagnostics",
        "transport_health": "WebSocket transport health diagnostics passthrough",
        "client_capabilities_for_entry": "static client capability flag source",
        "push_runtime_available": "active WebSocket availability guard",
    },
    "custom_components/yeelight_pro/device_display.py": {
        "device_type_label": "friendly picker device type summary",
        "channel_name_label": "friendly sub-entity channel label",
        "_CATEGORY_LABELS": "category label registry",
    },
    "custom_components/yeelight_pro/device_channel_semantics.py": {
        "uses_output_channel_label": "input/output channel naming semantics",
        "OUTPUT_CHANNEL_CATEGORIES": "relay output channel category guard",
        "EVENT_INPUT_CATEGORIES": "event input channel category guard",
    },
    "custom_components/yeelight_pro/device_channel_catalog.py": {
        "product_catalog_channel_count": "catalog-backed channel count helper",
        "is_input_channel_component_name": "input channel catalog name guard",
        "is_channel_component_name": "channel catalog name guard",
    },
    "custom_components/yeelight_pro/device_channel_generated_names.py": {
        "looks_like_generated_channel_name": "generated channel name replacement guard",
        "generated_channel_name_index": "generated channel index parser guard",
        "CHANNEL_NUMERAL_LABELS": "Chinese channel numeral label registry",
    },
    "custom_components/yeelight_pro/device_channels.py": {
        "channel_name_label": "friendly sub-entity channel label",
        "switch_channel_count_hint": "switch channel count inference",
        "_CHANNEL_LABELS": "indexed switch channel label registry",
        "_POSITIONAL_CHANNEL_LABELS": "physical switch position label registry",
    },
    "custom_components/yeelight_pro/projector/property_control_ownership.py": {
        "MAIN_ENTITY_PROPS": "main entity property exclusion registry",
        "MAIN_ENTITY_PROPS_BY_PLATFORM": "platform main-entity ownership map",
        "is_main_entity_property": "main entity ownership helper",
    },
}
