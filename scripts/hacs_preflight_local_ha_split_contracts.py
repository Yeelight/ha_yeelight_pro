"""Local HA release tokens for split-contract preflight registries."""

from __future__ import annotations

LOCAL_HA_SPLIT_CONTRACT_TOKENS = {
    "scripts/hacs_preflight_local_ha_split_contracts.py": {
        "LOCAL_HA_SPLIT_CONTRACT_TOKENS": "split-contract release token registry",
        "hacs_preflight_split_contracts.py": "split contract facade coverage",
        "hacs_preflight_split_client_contracts.py": (
            "split client contract token coverage"
        ),
    },
    "scripts/hacs_preflight_split_contracts.py": {
        "SPLIT_CONTRACT_TEST_TOKENS": "split contract token registry",
        "SPLIT_CLIENT_CONTRACT_TEST_TOKENS": "split client token import",
        "_SPLIT_CONFIG_FLOW_CONTRACT_TEST_TOKENS": "config-flow token registry",
        "test_capability_registry_contract.py": "capability split test guard",
        "config_flow_helpers.py": "config-flow helper split test guard",
        "test_config_flow_cloud.py": "config-flow cloud split test guard",
        "test_config_flow_cloud_devices.py": (
            "config-flow cloud device picker split test guard"
        ),
        "test_config_flow_entry_creation.py": (
            "config-flow entry creation split test guard"
        ),
        "test_config_flow_scan_login.py": "config-flow scan-login split test guard",
        "test_config_flow_scan_login_device.py": (
            "scan-login device id split test guard"
        ),
        "test_config_flow_scan_login_polling.py": (
            "scan-login polling split test guard"
        ),
        "test_config_flow_reauth.py": "config-flow reauth split test guard",
        "cloud reauth region isolation coverage": (
            "config-flow reauth region isolation guard"
        ),
        "scan-login device id privacy coverage": (
            "scan-login device privacy guard reason"
        ),
        "test_options_flow_contract.py": "options split test guard",
        "test_options_flow_device_picker.py": (
            "options real-device picker split test guard"
        ),
        "test_translation_runtime_contract.py": "translation split test guard",
        "scan-login LOGIN token flow coverage": "scan-login flow coverage reason",
        "manual device filter reload coverage": "device filter option coverage reason",
        "options real-device picker API coverage": (
            "options picker API coverage reason"
        ),
        "device picker friendly type label coverage": (
            "config-flow picker friendly type label reason"
        ),
        "options picker friendly type label coverage": (
            "options picker friendly type label reason"
        ),
        "Repairs placeholder runtime coverage": "Repair placeholder coverage reason",
    },
    "scripts/hacs_preflight_split_client_contracts.py": {
        "SPLIT_CLIENT_CONTRACT_TEST_TOKENS": "split client token registry",
        "p0_client_helpers.py": "P0 client helper split test guard",
        "test_p0_client_contracts.py": "P0 client contract split test guard",
        "test_push_payloads.py": "push payload split test guard",
        "config_entry_lifecycle_helpers.py": "config-entry helper split test guard",
        "test_config_entry_unload.py": "config-entry unload split test guard",
        "shared scan-login client fake coverage": "scan-login fake helper coverage reason",
        "push property payload normalization coverage": (
            "push payload adapter coverage reason"
        ),
        "failed unload runtime preservation coverage": (
            "config-entry unload failure coverage reason"
        ),
    },
}
