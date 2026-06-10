"""Release guard tokens for split contract tests."""

from __future__ import annotations

from scripts.hacs_preflight_split_client_contracts import (
    SPLIT_CLIENT_CONTRACT_TEST_TOKENS,
)

_SPLIT_CONFIG_FLOW_CONTRACT_TEST_TOKENS = {
    "tests/test_capability_registry_contract.py": {
        "test_event_aliases_cover_backend_event_types": (
            "backend event alias contract coverage"
        ),
        "test_capability_registry_maps_core_categories_and_properties": (
            "core category/property registry coverage"
        ),
        "multi spin": "scene panel multi-spin alias coverage",
        "human enter": "human sensor enter event alias coverage",
        "power.alarm": "power alarm event alias coverage",
        "platform_for_category": "category-to-platform facade coverage",
        "property_capability": "core property capability lookup coverage",
    },
    "tests/test_options_flow_contract.py": {
        "test_options_flow_shows_defaults": "options default form coverage",
        "test_options_flow_confirms_runtime_only_options": (
            "runtime-only option confirmation coverage"
        ),
        "test_options_flow_confirms_reload_required_options": (
            "reload-required option confirmation coverage"
        ),
        "test_options_flow_manual_device_filter_requires_reload": (
            "manual device filter reload coverage"
        ),
        "test_coordinator_scan_interval_reads_entry_options": (
            "coordinator runtime scan interval coverage"
        ),
        "CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES": (
            "manual device filter id coverage"
        ),
        "get_enabled_platforms": "experimental platform default gate coverage",
        "test_enabled_platforms_hide_experimental_by_default": (
            "experimental platform default-off coverage"
        ),
        "EXPERIMENTAL_PLATFORMS": "experimental platform constant coverage",
    },
    "tests/test_options_flow_device_picker.py": {
        "test_options_flow_cloud_entry_shows_real_device_picker_opener": (
            "options real-device picker opener coverage"
        ),
        "test_options_flow_private_entry_hides_real_device_picker_opener": (
            "options private-entry picker hidden coverage"
        ),
        "test_options_flow_real_device_picker_loads_current_cloud_devices": (
            "options real-device picker API coverage"
        ),
        "test_options_flow_real_device_picker_selection_requires_reload": (
            "options real-device picker reload coverage"
        ),
        "test_options_flow_real_device_picker_load_error_is_redacted": (
            "options real-device picker redaction coverage"
        ),
        "CONF_DEVICE_IMPORT_FILTER_PICKER": "options picker opener field coverage",
        "Kitchen Secret": "options picker label privacy marker",
    },
    "tests/test_translation_runtime_contract.py": {
        "test_translations_are_valid_and_key_aligned": (
            "translation leaf-key alignment coverage"
        ),
        "test_topology_repair_placeholders_match_translations": (
            "Repairs placeholder runtime coverage"
        ),
        "test_scan_login_translations_keep_qr_countdown_and_refresh_guidance": (
            "scan-login QR countdown translation coverage"
        ),
        "leaf_paths": "shared translation path helper reuse",
        "Yeelight APP 1.5.0": "scan-login APP version translation guard",
        "{remaining_seconds}": "scan-login countdown placeholder translation guard",
        "{poll_count}": "scan-login poll-count placeholder translation guard",
        "CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES": (
            "device filter include translation coverage"
        ),
        "refresh_product_schemas": "refresh service field translation coverage",
        "device_topology_changed": "topology Repair issue translation coverage",
    },
    "tests/config_flow_helpers.py": {
        "def config_flow": "shared config-flow fixture coverage",
        "prepare_cloud_flow": "shared cloud flow setup coverage",
    },
    "tests/conftest.py": {
        "config_flow_helpers": "shared config-flow fixture plugin registration",
    },
    "tests/test_config_flow.py": {
        "test_cloud_auth_method_schema_uses_localized_labels": (
            "config-flow auth method label coverage"
        ),
        "test_cloud_region_schema_uses_localized_region_selector": (
            "config-flow region selector coverage"
        ),
        "test_user_schema_uses_localized_connection_mode_selector": (
            "config-flow connection mode selector coverage"
        ),
        'translation_key"] == "cloud_auth_method"': (
            "cloud auth method selector translation-key coverage"
        ),
        'translation_key"] == "connection_mode"': (
            "connection mode selector translation-key coverage"
        ),
        'translation_key"] == "cloud_region"': (
            "cloud region selector translation-key coverage"
        ),
    },
    "tests/test_config_flow_cloud.py": {
        "test_cloud_region_selects_documented_multi_region_domain": (
            "multi-region cloud domain coverage"
        ),
        "test_cloud_auth_method_routes_to_scan_login": (
            "scan-login auth path coverage"
        ),
        "test_cloud_auth_method_routes_to_manual_token": (
            "manual token auth path coverage"
        ),
        "test_cloud_houses_maps_load_errors_to_form": (
            "cloud house load error mapping coverage"
        ),
        "test_cloud_houses_user_selection_opens_real_device_picker": (
            "cloud house to real device picker coverage"
        ),
    },
    "tests/test_config_flow_cloud_devices.py": {
        "test_cloud_devices_loads_real_devices_and_defaults_to_all": (
            "real cloud device picker API coverage"
        ),
        "test_cloud_devices_can_continue_without_filter_after_load_error": (
            "device picker load-error continue without filter coverage"
        ),
        "test_cloud_devices_user_selection_creates_filtered_entry": (
            "real device picker import-filter persistence coverage"
        ),
        "test_cloud_devices_entry_options_store_ids_not_picker_labels": (
            "real device picker options privacy coverage"
        ),
    },
    "tests/test_config_flow_entry_creation.py": {
        "test_create_entry_persists_open_api_client_id": (
            "Open API clientId persistence coverage"
        ),
        "test_create_entry_manual_token_unique_id_uses_redacted_token_fingerprint": (
            "manual token multi-account redacted unique-id coverage"
        ),
        "test_create_entry_manual_token_unique_id_separates_accounts": (
            "manual token multi-account separation coverage"
        ),
        "test_scan_login_account_key_uses_redacted_token_fingerprint_without_metadata": "scan-login token fingerprint fallback coverage",
        "test_scan_login_account_key_ignores_blank_user_id_alias": "blank account id token-fingerprint fallback coverage",
    },
    "tests/test_config_flow_device_picker.py": {
        "test_device_choices_normalize_open_api_rows": (
            "device picker Open API row normalization coverage"
        ),
        "test_cloud_devices_schema_uses_multi_select_options": (
            "device picker multi-select schema coverage"
        ),
        "test_selected_device_filter_includes_only_selected_devices": (
            "device picker import filter coverage"
        ),
        "test_selected_device_filter_drops_unknown_selected_ids": (
            "device picker unknown id rejection coverage"
        ),
        "test_selected_device_ids_from_input_drops_unknown_choices": (
            "device picker input unknown id rejection coverage"
        ),
        "NO_DEVICE_SELECTED_SENTINEL": "device picker import-none sentinel coverage",
    },
    "config_flow_device_picker.py": {
        "async_load_device_choices": "cloud device picker API loader",
        "get_devices(house_id)": "cloud device picker uses house device list",
        "device_import_filter_for_selected_devices": (
            "cloud device picker filter builder"
        ),
        "allowed_device_ids": "device picker input allowlist",
        "SelectSelectorConfig": "Home Assistant native device multi-select",
        "CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES": (
            "device picker writes existing import filter option"
        ),
    },
    "options_flow.py": {
        "async_step_cloud_devices": "options real-device picker step",
        "async_load_device_choices": "options picker real cloud device loader",
        "merge_options_device_picker": "options picker canonical filter merge",
        "selected_device_ids_from_options": "options picker current selection helper",
        "confirm_reload": "options picker reload confirmation boundary",
    },
    "tests/test_config_flow_oauth.py": {
        "test_cloud_scan_login_initial_step_creates_qrcode": (
            "scan-login qrcode creation coverage"
        ),
        'selector_type == "qr_code"': "native Home Assistant QR selector coverage",
        "CONF_SCAN_LOGIN_QRCODE": "scan-login QR selector field coverage",
        "test_cloud_scan_login_submit_starts_continuous_progress_poll": (
            "scan-login progress polling coverage"
        ),
        "test_cloud_scan_login_progress_done_loads_houses": (
            "scan-login LOGIN token flow coverage"
        ),
        "test_cloud_scan_login_rejects_different_region": (
            "initial scan-login region isolation coverage"
        ),
        "test_cloud_scan_login_expired_qrcode_requires_manual_refresh": (
            "scan-login expired QR manual refresh coverage"
        ),
        "test_cloud_scan_login_poll_timeout_returns_expired_error": (
            "scan-login polling timeout UX coverage"
        ),
        "test_cloud_auth_method_no_longer_routes_to_oauth_app": (
            "authorization-code UI downgrade coverage"
        ),
        "CONF_SCAN_LOGIN_REFRESH": "scan-login qrcode refresh form coverage",
    },
    "tests/test_config_flow_scan_login_polling.py": {
        "test_scan_login_poll_task_keeps_polling_until_login": (
            "continuous scan-login polling coverage"
        ),
        "test_scan_login_needs_refresh_keeps_expired_qrcode_for_manual_refresh": (
            "scan-login expired QR no auto-refresh coverage"
        ),
        "test_scan_login_description_placeholders_expose_pollable_state": (
            "scan-login description placeholder coverage"
        ),
        "test_scan_login_poll_task_stops_when_local_qrcode_ttl_expires": (
            "scan-login local TTL stop coverage"
        ),
    },
    "tests/test_config_flow_scan_login_device.py": {
        "test_scan_login_device_id_hashes_ha_instance_id_without_leaking_raw_id": (
            "scan-login device id privacy coverage"
        ),
        "test_scan_login_device_id_changes_for_different_ha_instance_ids": (
            "scan-login device id uniqueness coverage"
        ),
    },
    "tests/test_config_flow_reauth.py": {
        "test_cloud_reauth_routes_to_scan_login_qrcode": (
            "cloud reauth scan-login routing coverage"
        ),
        "test_cloud_reauth_scan_login_updates_token_metadata": (
            "cloud reauth scan-login token update coverage"
        ),
        "test_cloud_reauth_scan_login_rejects_different_account": (
            "cloud reauth account isolation coverage"
        ),
        "test_cloud_reauth_scan_login_rejects_different_region": (
            "cloud reauth region isolation coverage"
        ),
        "test_reauth_update_normalizes_entry_data_and_preserves_client_id": (
            "reauth entry normalization coverage"
        ),
        "test_config_flow_unknown_errors_log_only_exception_type": (
            "config-flow unknown error redaction coverage"
        ),
        "secret-token": "sensitive token log redaction marker",
    },
    "tests/test_config_flow_reauth_identity.py": {
        "test_cloud_reauth_rejects_different_token_without_account_metadata": "metadata-less token mismatch rejection coverage",
        "test_cloud_reauth_ignores_blank_stored_user_id_for_identity": "blank stored user id reauth rejection coverage",
        "test_cloud_reauth_accepts_matching_token_fingerprint_without_metadata": "metadata-less token fingerprint match coverage",
    },
    "config_flow_account.py": {"redacted_token_fingerprint": "shared token fingerprint helper"},
    "config_flow_reauth.py": {
        "ReauthConfigFlowMixin": "split reauth config-flow mixin",
        "async_step_cloud_scan_login": "cloud reauth routes through scan login",
        "_same_reauth_account": "cloud reauth account isolation guard",
        "_same_reauth_region": "cloud reauth region isolation guard",
        "scan_login_token_matches_region": "shared scan-login region guard",
        "async_step_reauth_confirm": "private manual token reauth boundary",
    },
    "config_flow_scan_login_helpers.py": {
        "ScanLoginFlowState": "scan-login flow state helper split",
        "async_poll_scan_login_until_login": "continuous scan-login polling helper",
        "cloud_scan_login_schema_for_qrcode": "QR-code schema builder",
        "scan_login_account_key": "scan-login account-key helper",
        "QrCodeSelector": "Home Assistant native QR-code selector",
    },
    "config_flow_scan_login_region.py": {
        "scan_login_token_matches_region": "shared scan-login region guard",
        "normalize_cloud_region": "scan-login region alias normalization",
    },
}

SPLIT_CONTRACT_TEST_TOKENS = {
    **_SPLIT_CONFIG_FLOW_CONTRACT_TEST_TOKENS,
    **SPLIT_CLIENT_CONTRACT_TEST_TOKENS,
}
