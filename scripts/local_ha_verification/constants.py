"""Constants for local HA verification."""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMPONENT_ROOT = ROOT / "custom_components" / "yeelight_pro"
DOMAIN = "yeelight_pro"

DEFAULT_CONTAINER = "lucore-ha-verify"
DEFAULT_HA_URL = "http://localhost:18124"
DEFAULT_ENTITY_COUNTS = {
    "button": 31,
    "light": 43,
    "number": 14,
    "scene": 20,
    "select": 3,
    "switch": 29,
}
DEFAULT_EXPECTED_ENTITIES = sum(DEFAULT_ENTITY_COUNTS.values())
DEFAULT_EXPECTED_DEVICES = 2
DEFAULT_EXPECTED_CONFIG_ENTRIES = 1

EXCLUDED_COMPARE_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "tests",
}
EXCLUDED_COMPARE_SUFFIXES = {".pyc", ".pyo"}
FORBIDDEN_INSTALL_PARTS = {
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
    "tests",
}
FORBIDDEN_INSTALL_NAMES = {
    ".coverage",
    "coverage.json",
    "coverage.xml",
    "text.py",
    "yeelight_pro.zip",
}
REQUIRED_SERVICES = {
    "assign_areas",
    "auto_assign_areas",
    "cleanup_registry",
    "debug_emit_event",
    "refresh",
}
REQUIRED_RUNTIME_MODULES = (
    "custom_components.yeelight_pro.refresh_service",
    "custom_components.yeelight_pro.registry_cleanup_service",
    "custom_components.yeelight_pro.lan_contract",
    "custom_components.yeelight_pro.lan_discovery",
    "custom_components.yeelight_pro.lan_methods",
    "custom_components.yeelight_pro.lan_payload",
    "custom_components.yeelight_pro.lan_runtime",
    "custom_components.yeelight_pro.live_runtime",
    "custom_components.yeelight_pro.scan_login_contract",
    "custom_components.yeelight_pro.projector.event_helpers",
    "custom_components.yeelight_pro.projector.sensor_helpers",
    "custom_components.yeelight_pro.push_contract",
    "custom_components.yeelight_pro.push_manager",
    "custom_components.yeelight_pro.push_transport",
    "custom_components.yeelight_pro.capabilities.spec_correction_normalizers",
    "custom_components.yeelight_pro.converter.runtime_inference_helpers",
    "custom_components.yeelight_pro.config_flow_account",
    "custom_components.yeelight_pro.config_flow_device_picker",
    "custom_components.yeelight_pro.entry_title",
    "custom_components.yeelight_pro.config_flow_options",
    "custom_components.yeelight_pro.config_flow_reauth",
    "custom_components.yeelight_pro.config_flow_scan_login",
    "custom_components.yeelight_pro.config_flow_scan_login_helpers",
    "custom_components.yeelight_pro.config_flow_scan_login_region",
    "custom_components.yeelight_pro.core.schema_cache",
    "custom_components.yeelight_pro.core.client",
    "custom_components.yeelight_pro.core.client_node_base",
    "custom_components.yeelight_pro.core.client_node_api",
    "custom_components.yeelight_pro.core.client_node_lists",
    "custom_components.yeelight_pro.core.client_node_properties",
    "custom_components.yeelight_pro.core.client_request",
    "custom_components.yeelight_pro.core.coordinator_controls",
    "custom_components.yeelight_pro.core.device_metadata",
    "custom_components.yeelight_pro.core.lan_control",
    "custom_components.yeelight_pro.core.coordinator_runtime",
    "custom_components.yeelight_pro.core.scan_login",
    "custom_components.yeelight_pro.core.runtime_bridge",
    "custom_components.yeelight_pro.diagnostics",
    "custom_components.yeelight_pro.diagnostic_inventory",
    "custom_components.yeelight_pro.diagnostic_options",
    "custom_components.yeelight_pro.diagnostic_payloads",
    "custom_components.yeelight_pro.device_trigger",
    "custom_components.yeelight_pro.entity_lifecycle_cleanup",
    "custom_components.yeelight_pro.ha_device_registry",
    "custom_components.yeelight_pro.repair_issues",
    "custom_components.yeelight_pro.debug_service",
    "custom_components.yeelight_pro.registry_cleanup_service",
)
SENSITIVE_CACHE_MARKERS = {
    "access_token",
    "accesstoken",
    "authorization",
    "device_id",
    "deviceid",
    "deviceids",
    "devices",
    "house_id",
    "houseid",
    "houseids",
    "houses",
    "localtoken",
    "mac",
    "mac_address",
    "macaddress",
    "password",
    "private_domain",
    "privatedomain",
    "raw_payload",
    "rawpayload",
    "room_id",
    "roomid",
    "roomids",
    "roomname",
    "rooms",
    "token",
    "username",
}
SENSITIVE_CACHE_VALUE_PATTERNS = (
    re.compile(r"\bbearer\s+[a-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\b(?:access_)?token\s*[:=]", re.IGNORECASE),
    re.compile(r"\bauthorization\s*[:=]", re.IGNORECASE),
    re.compile(r"\bhouse(?:_?id)?\s*[:=]", re.IGNORECASE),
    re.compile(r"\bdevice(?:_?id)?\s*[:=]", re.IGNORECASE),
    re.compile(r"\broom(?:_?id)?\s*[:=]", re.IGNORECASE),
    re.compile(r"\bmac(?:_address)?\s*[:=]", re.IGNORECASE),
)
BAD_LOG_MARKERS = {
    "ERROR",
    "ImportError",
    "ModuleNotFoundError",
    "Traceback",
}
YEELIGHT_LOG_MARKERS = {
    "custom_components.yeelight_pro",
    "custom_components/yeelight_pro",
    "yeelight_pro",
}
