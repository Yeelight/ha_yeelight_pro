"""Additional runtime component source contract tokens."""

from __future__ import annotations

LOCAL_HA_RUNTIME_ADDITIONAL_SOURCE_TOKENS = {
    "custom_components/yeelight_pro/config_flow_private.py": {
        "PrivateConfigFlowMixin": "private deployment config-flow split mixin",
        "CONF_PRIVATE_PUSH_DOMAIN": "private deployment independent push endpoint field",
        "deployment_push_base_url": "private deployment push URL normalization",
        "async_step_cloud_auth_method": "shared cloud/private auth flow handoff",
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
        "deployment_push_base_url(private_push_domain)": (
            "private push endpoint priority over API host fallback"
        ),
    },
}
