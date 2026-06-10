"""Analytics release-preflight contract tokens."""

from __future__ import annotations

from pathlib import Path

from scripts.hacs_preflight_contracts import _check_no_network, _require_tokens


def check_analytics_contract_tests(component_root: Path) -> list[str]:
    """Ensure data-analysis API contracts stay no-network and explicit."""
    errors: list[str] = []
    required_files = {
        "analytics_contract.py": {
            "ANALYTICS_ALARM_ANALYSE": "alarm analyse endpoint key",
            "ANALYTICS_ALARM_TOP": "alarm top endpoint key",
            "ANALYTICS_ALARM_TREND": "alarm trend endpoint key",
            "ANALYTICS_ENERGY_ANALYSE": "energy analyse endpoint key",
            "ANALYTICS_ENERGY_TREND": "energy trend endpoint key",
            "ANALYTICS_ACTION_DAY": "daily action endpoint key",
            "ANALYTICS_ACTION_MONTH": "monthly action endpoint key",
            "ANALYTICS_ACTION_YEAR": "yearly action endpoint key",
            "ANALYTICS_METHOD_POST": "documented analytics POST method",
            "analytics_method": "analytics method helper",
            "analytics_request_path": "complete analytics path builder",
            "area_supported": "documented areaId boundary",
        },
        "tests/test_analytics_contract.py": {
            "test_analytics_paths_match_documented_endpoints": "analytics path coverage",
            "alarm/analyse": "alarm analyse path coverage",
            "alarm/top": "alarm top path coverage",
            "alarm/trend": "alarm trend path coverage",
            "energy/analyse": "energy analyse path coverage",
            "energy/trend": "energy trend path coverage",
            "action/r/day": "daily action path coverage",
            "action/r/month": "monthly action path coverage",
            "action/r/year": "yearly action path coverage",
            "test_analytics_methods_match_documented_post_contract": "analytics method coverage",
            "test_action_analytics_query_uses_documented_date_shape": "action date shape coverage",
            "test_analytics_query_rejects_wrong_shape_or_unsupported_area": (
                "analytics date/area boundary coverage"
            ),
        },
        "analytics_runtime.py": {
            "math.isfinite": "analytics finite numeric guard",
            "__slots__": "analytics runtime raw payload storage guard",
        },
        "tests/test_analytics_runtime.py": {
            "test_analytics_runtime_state_cannot_retain_raw_payload_attribute": (
                "analytics runtime no raw payload attribute coverage"
            ),
            "test_analytics_runtime_drops_non_finite_numeric_values": (
                "analytics non-finite numeric rejection coverage"
            ),
            "device-secret": "analytics runtime raw id redaction marker",
        },
        "tests/test_analytics_service.py": {
            "GROUP_ID_ADMIN": "analytics service admin-user coverage",
            "test_refresh_analytics_service_rejects_missing_user_context": (
                "analytics service missing context rejection coverage"
            ),
            "test_refresh_analytics_service_rejects_disabled_entry": (
                "analytics runtime explicit opt-in service coverage"
            ),
            "test_refresh_analytics_service_returns_redacted_aggregate_response": (
                "analytics aggregate-only service response coverage"
            ),
            "test_refresh_analytics_service_strips_raw_error_cause": (
                "analytics service raw error redaction coverage"
            ),
            "secret-token": "analytics service secret redaction marker",
        },
        "scripts/verify_analytics.py": {
            "confirm-production-analytics": (
                "production analytics explicit confirm flag"
            ),
            "YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN": (
                "production analytics token env guard"
            ),
            "YEELIGHT_PRO_ANALYTICS_HOUSE_ID": (
                "production analytics house env guard"
            ),
            "validate_run_request": "production analytics fail-closed safety gate",
            "async_probe_analytics": "production analytics probe entrypoint",
        },
        "scripts/verify_analytics_support.py": {
            "AnalyticsProbeSummary": "production analytics safe summary",
            "update_summary_from_payload": (
                "production analytics aggregate-only payload summary"
            ),
            "object_shapes": "production analytics object-shape summary",
            "numeric_fields": "production analytics numeric-field summary",
            "load_yeelight_client": "production analytics client loader",
        },
        "tests/test_verify_analytics.py": {
            "test_validate_run_request_requires_explicit_confirm": (
                "production analytics confirm guard coverage"
            ),
            "test_validate_run_request_requires_token_and_house_env": (
                "production analytics token and house env coverage"
            ),
            "YEELIGHT_PRO_ANALYTICS_AREA_ID": (
                "production analytics optional area env coverage"
            ),
            "test_validate_run_request_rejects_invalid_region_endpoint_and_timeout": (
                "production analytics bounded request coverage"
            ),
            "test_summary_describes_payload_shape_without_raw_values": (
                "production analytics raw payload redaction coverage"
            ),
            "test_main_does_not_probe_network_without_confirm": (
                "production analytics default no-network coverage"
            ),
            "test_script_path_execution_is_no_network_without_confirm": (
                "production analytics script-path no-network coverage"
            ),
            "test_probe_summarizes_analytics_payload_without_values": (
                "production analytics fake-payload aggregate coverage"
            ),
        },
    }

    _require_tokens(component_root, required_files, errors, "analytics contract requires")
    _check_no_network(component_root, ("analytics_contract.py",), errors)
    return errors


__all__ = ["check_analytics_contract_tests"]
