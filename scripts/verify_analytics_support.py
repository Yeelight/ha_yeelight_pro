"""Support helpers for the guarded production analytics probe."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = ROOT / "custom_components" / "yeelight_pro"
MAX_SHAPE_DEPTH = 2


@dataclass(slots=True)
class AnalyticsProbeSummary:
    """Diagnostics-safe aggregate summary for one analytics probe."""

    ok: bool = False
    network_attempted: bool = False
    region: str = "cn"
    endpoint: str = "energy_analyse"
    top_level_type: str = "unknown"
    field_types: Counter[str] = field(default_factory=Counter)
    numeric_fields: Counter[str] = field(default_factory=Counter)
    list_lengths: Counter[str] = field(default_factory=Counter)
    object_shapes: Counter[str] = field(default_factory=Counter)
    last_error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary without raw payload or identifiers."""
        return {
            "ok": self.ok,
            "network_attempted": self.network_attempted,
            "region": self.region,
            "endpoint": self.endpoint,
            "top_level_type": self.top_level_type,
            "field_types": dict(sorted(self.field_types.items())),
            "numeric_fields": dict(sorted(self.numeric_fields.items())),
            "list_lengths": dict(sorted(self.list_lengths.items())),
            "object_shapes": dict(sorted(self.object_shapes.items())),
            "last_error_type": self.last_error_type,
        }


def update_summary_from_payload(
    summary: AnalyticsProbeSummary,
    payload: Any,
) -> None:
    """Copy only field-shape and type aggregates into the summary."""
    summary.top_level_type = _safe_type_name(payload)
    summary.field_types.clear()
    summary.numeric_fields.clear()
    summary.list_lengths.clear()
    summary.object_shapes.clear()
    _summarize_value(summary, payload, path="$", depth=0)


def analytics_request_path(
    house_id: int,
    endpoint: str,
    *,
    date_code: str | None,
    start_date: str | None,
    end_date: str | None,
    area_id: str | None,
) -> str:
    """Validate and build the analytics path through the source contract."""
    contract = load_analytics_contract()
    return str(
        contract.analytics_request_path(
            house_id,
            endpoint,
            date_code=date_code,
            start_date=start_date,
            end_date=end_date,
            area_id=area_id,
        )
    )


def normalize_cloud_region(region: str) -> str:
    """Return the normalized Yeelight cloud region alias."""
    contract = load_scan_login_contract()
    return str(contract.normalize_cloud_region(region))


def iot_domain_for_region(region: str) -> str:
    """Return the documented Open API IoT domain for one region."""
    contract = load_scan_login_contract()
    return str(contract.iot_base_url(region))


def load_yeelight_client() -> Any:
    """Load the Yeelight client after safety checks pass."""
    ensure_probe_package()
    modules = (
        ("yeelight_pro_analytics_probe.const", COMPONENT_ROOT / "const.py"),
        ("yeelight_pro_analytics_probe.utils", COMPONENT_ROOT / "utils.py"),
        ("yeelight_pro_analytics_probe.core.exceptions", COMPONENT_ROOT / "core" / "exceptions.py"),
        ("yeelight_pro_analytics_probe.core.http_errors", COMPONENT_ROOT / "core" / "http_errors.py"),
        ("yeelight_pro_analytics_probe.core.client_request", COMPONENT_ROOT / "core" / "client_request.py"),
        ("yeelight_pro_analytics_probe.capabilities.models", COMPONENT_ROOT / "capabilities" / "models.py"),
        ("yeelight_pro_analytics_probe.capabilities.data", COMPONENT_ROOT / "capabilities" / "data.py"),
        ("yeelight_pro_analytics_probe.capabilities.registry", COMPONENT_ROOT / "capabilities" / "registry.py"),
        ("yeelight_pro_analytics_probe.core.schema_cache", COMPONENT_ROOT / "core" / "schema_cache.py"),
        ("yeelight_pro_analytics_probe.analytics_contract", COMPONENT_ROOT / "analytics_contract.py"),
        ("yeelight_pro_analytics_probe.core.client_paths", COMPONENT_ROOT / "core" / "client_paths.py"),
        ("yeelight_pro_analytics_probe.core.client_helpers", COMPONENT_ROOT / "core" / "client_helpers.py"),
        ("yeelight_pro_analytics_probe.core.client_node_base", COMPONENT_ROOT / "core" / "client_node_base.py"),
        ("yeelight_pro_analytics_probe.core.client_analytics", COMPONENT_ROOT / "core" / "client_analytics.py"),
        ("yeelight_pro_analytics_probe.core.client_node_lists", COMPONENT_ROOT / "core" / "client_node_lists.py"),
        ("yeelight_pro_analytics_probe.core.client_node_properties", COMPONENT_ROOT / "core" / "client_node_properties.py"),
        ("yeelight_pro_analytics_probe.core.client_node_api", COMPONENT_ROOT / "core" / "client_node_api.py"),
        ("yeelight_pro_analytics_probe.oauth_contract", COMPONENT_ROOT / "oauth_contract.py"),
        ("yeelight_pro_analytics_probe.scan_login_contract", COMPONENT_ROOT / "scan_login_contract.py"),
        ("yeelight_pro_analytics_probe.core.oauth", COMPONENT_ROOT / "core" / "oauth.py"),
        ("yeelight_pro_analytics_probe.core.scan_login", COMPONENT_ROOT / "core" / "scan_login.py"),
        ("yeelight_pro_analytics_probe.core.client", COMPONENT_ROOT / "core" / "client.py"),
    )
    for module_name, path in modules:
        if module_name not in sys.modules:
            load_probe_module(module_name, path)
    return sys.modules["yeelight_pro_analytics_probe.core.client"].YeelightProClient


def load_analytics_contract() -> Any:
    """Load analytics helpers without importing Home Assistant."""
    ensure_probe_package()
    module_name = "yeelight_pro_analytics_probe.core.exceptions"
    if module_name not in sys.modules:
        load_probe_module(module_name, COMPONENT_ROOT / "core" / "exceptions.py")
    return load_probe_module(
        "yeelight_pro_analytics_probe.analytics_contract",
        COMPONENT_ROOT / "analytics_contract.py",
    )


def load_scan_login_contract() -> Any:
    """Load region helpers without importing Home Assistant."""
    ensure_probe_package()
    for module_name, path in (
        ("yeelight_pro_analytics_probe.core.exceptions", COMPONENT_ROOT / "core" / "exceptions.py"),
        ("yeelight_pro_analytics_probe.core.http_errors", COMPONENT_ROOT / "core" / "http_errors.py"),
        ("yeelight_pro_analytics_probe.const", COMPONENT_ROOT / "const.py"),
        ("yeelight_pro_analytics_probe.oauth_contract", COMPONENT_ROOT / "oauth_contract.py"),
    ):
        if module_name not in sys.modules:
            load_probe_module(module_name, path)
    return load_probe_module(
        "yeelight_pro_analytics_probe.scan_login_contract",
        COMPONENT_ROOT / "scan_login_contract.py",
    )


def ensure_probe_package() -> None:
    """Create isolated package namespaces for relative client imports."""
    package = sys.modules.get("yeelight_pro_analytics_probe")
    if package is None:
        package = types.ModuleType("yeelight_pro_analytics_probe")
        package.__path__ = [str(COMPONENT_ROOT)]  # type: ignore[attr-defined]
        sys.modules["yeelight_pro_analytics_probe"] = package
    for name, path in (
        ("capabilities", COMPONENT_ROOT / "capabilities"),
        ("core", COMPONENT_ROOT / "core"),
    ):
        module_name = f"yeelight_pro_analytics_probe.{name}"
        if module_name not in sys.modules:
            module = types.ModuleType(module_name)
            module.__path__ = [str(path)]  # type: ignore[attr-defined]
            sys.modules[module_name] = module


def load_probe_module(module_name: str, path: Path) -> Any:
    """Load a Yeelight module inside the isolated probe namespace."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{path.name} module is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _summarize_value(
    summary: AnalyticsProbeSummary,
    value: Any,
    *,
    path: str,
    depth: int,
) -> None:
    """Summarize a value without copying identifiers or raw payload values."""
    value_type = _safe_type_name(value)
    summary.field_types[f"{path}:{value_type}"] += 1
    if isinstance(value, bool):
        return
    if isinstance(value, int | float):
        summary.numeric_fields[path] += 1
        return
    if depth >= MAX_SHAPE_DEPTH:
        return
    if isinstance(value, Mapping):
        summary.object_shapes[_shape_key(value)] += 1
        for key, child in value.items():
            _summarize_value(
                summary,
                child,
                path=f"{path}.{_safe_key(key)}",
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        summary.list_lengths[f"{path}:{_length_bucket(len(value))}"] += 1
        for child in value[:3]:
            _summarize_value(
                summary,
                child,
                path=f"{path}[]",
                depth=depth + 1,
            )


def _safe_key(value: Any) -> str:
    """Return a field name only, without field values."""
    text = str(value).strip()
    return text if text else "<empty>"


def _shape_key(payload: Mapping[str, Any]) -> str:
    """Return a field-name-only shape key for a JSON object."""
    safe_keys = sorted(_safe_key(key) for key in payload)
    return ",".join(safe_keys) if safe_keys else "<empty>"


def _safe_type_name(value: Any) -> str:
    """Return a stable low-cardinality type label."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, Mapping):
        return "object"
    return "other"


def _length_bucket(length: int) -> str:
    """Bucket list lengths to avoid exposing exact large payload cardinality."""
    if length == 0:
        return "0"
    if length <= 3:
        return "1-3"
    if length <= 10:
        return "4-10"
    return "gt10"


__all__ = [
    "AnalyticsProbeSummary",
    "analytics_request_path",
    "iot_domain_for_region",
    "load_yeelight_client",
    "normalize_cloud_region",
    "update_summary_from_payload",
]
