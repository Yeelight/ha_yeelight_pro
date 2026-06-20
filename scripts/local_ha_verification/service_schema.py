"""Service schema contract verification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .report import VerificationReport
from .service_schema_runtime import (
    registered_service_schema_fields as _registered_service_schema_fields,
)


@dataclass(frozen=True)
class ServiceFieldContract:
    """Expected public service field shape."""

    required: bool
    selector: str


SERVICE_FIELD_CONTRACTS: dict[str, dict[str, ServiceFieldContract]] = {
    "assign_areas": {
        "devices": ServiceFieldContract(required=True, selector="object"),
        "area_id": ServiceFieldContract(required=True, selector="area"),
    },
    "auto_assign_areas": {
        "gateway_id": ServiceFieldContract(required=False, selector="text"),
    },
    "debug_emit_event": {
        "entry_id": ServiceFieldContract(required=False, selector="text"),
        "source_device_id": ServiceFieldContract(required=True, selector="text"),
        "component_id": ServiceFieldContract(required=True, selector="text"),
        "event_type": ServiceFieldContract(required=True, selector="text"),
        "event_attributes": ServiceFieldContract(required=False, selector="object"),
    },
    "debug_dump_push_health": {
        "entry_id": ServiceFieldContract(required=False, selector="text"),
    },
    "debug_emit_push_payload": {
        "entry_id": ServiceFieldContract(required=False, selector="text"),
        "source_device_id": ServiceFieldContract(required=False, selector="text"),
        "entity_id": ServiceFieldContract(required=False, selector="entity"),
        "node_type": ServiceFieldContract(required=False, selector="number"),
        "payload_shape": ServiceFieldContract(required=False, selector="select"),
        "params": ServiceFieldContract(required=True, selector="object"),
    },
    "refresh": {
        "entry_id": ServiceFieldContract(required=False, selector="text"),
        "refresh_product_schemas": ServiceFieldContract(
            required=False,
            selector="boolean",
        ),
    },
    "cleanup_registry": {
        "entry_id": ServiceFieldContract(required=False, selector="text"),
        "confirm": ServiceFieldContract(required=False, selector="boolean"),
        "audit_id": ServiceFieldContract(required=False, selector="text"),
    },
}


def verify_service_schema_contracts(
    install_root: Path,
    content: str,
    report: VerificationReport,
) -> None:
    """Verify services.yaml fields match runtime service schemas."""
    documented_fields = documented_service_field_contracts(content)
    runtime_fields = registered_service_schema_fields(install_root)
    failure_count = len(report.failures)

    _compare_field_contracts(
        report,
        label="services.yaml field schema",
        actual=documented_fields,
        check_selectors=True,
    )
    _compare_field_contracts(
        report,
        label="runtime service schema",
        actual=runtime_fields,
        check_selectors=False,
    )

    if len(report.failures) == failure_count:
        field_counts = {
            service: len(fields)
            for service, fields in sorted(SERVICE_FIELD_CONTRACTS.items())
        }
        report.fact(f"service field schemas: {field_counts}")
    report.metric(
        "service_field_schemas",
        {
            service: {
                field: _actual_required(contract)
                for field, contract in sorted(fields.items())
            }
            for service, fields in sorted(runtime_fields.items())
        },
    )


def documented_service_field_contracts(
    content: str,
) -> dict[str, dict[str, ServiceFieldContract]]:
    """Extract field required flags and selectors from services.yaml text."""
    services: dict[str, dict[str, dict[str, object]]] = {}
    current_service: str | None = None
    current_field: str | None = None
    in_fields = False
    in_selector = False

    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0 and line.endswith(":"):
            current_service = line[:-1]
            services.setdefault(current_service, {})
            current_field = None
            in_fields = False
            in_selector = False
            continue
        if current_service is None:
            continue
        if indent == 2:
            in_fields = line == "fields:"
            current_field = None
            in_selector = False
            continue
        if not in_fields:
            continue
        if indent == 4 and line.endswith(":"):
            current_field = line[:-1]
            services[current_service].setdefault(current_field, {})
            in_selector = False
            continue
        if current_field is None:
            continue
        if indent == 6 and line.startswith("required:"):
            services[current_service][current_field]["required"] = (
                line.split(":", 1)[1].strip().lower() == "true"
            )
            in_selector = False
            continue
        if indent == 6 and line == "selector:":
            in_selector = True
            continue
        if in_selector and indent == 8 and line.endswith(":"):
            services[current_service][current_field]["selector"] = line[:-1]
            in_selector = False

    return {
        service: {
            field: ServiceFieldContract(
                required=bool(values.get("required", False)),
                selector=str(values.get("selector", "")),
            )
            for field, values in fields.items()
        }
        for service, fields in services.items()
    }


def registered_service_schema_fields(
    install_root: Path,
) -> dict[str, dict[str, bool]]:
    """Return runtime service schema fields keyed by service name."""
    return _registered_service_schema_fields(install_root)


def _compare_field_contracts(
    report: VerificationReport,
    *,
    label: str,
    actual: dict[str, dict[str, ServiceFieldContract]] | dict[str, dict[str, bool]],
    check_selectors: bool,
) -> None:
    """Compare one service field layer with the release contract."""
    for service, expected_fields in sorted(SERVICE_FIELD_CONTRACTS.items()):
        actual_fields = actual.get(service)
        if actual_fields is None:
            report.fail(f"{label} missing service: {service}")
            continue
        missing = sorted(set(expected_fields) - set(actual_fields))
        unexpected = sorted(set(actual_fields) - set(expected_fields))
        if missing:
            report.fail(f"{label} missing fields for {service}: {missing}")
        if unexpected:
            report.fail(f"{label} unexpected fields for {service}: {unexpected}")
        for field, expected in sorted(expected_fields.items()):
            if field not in actual_fields:
                continue
            actual_required = _actual_required(actual_fields[field])
            if actual_required != expected.required:
                report.fail(
                    f"{label} required mismatch for {service}.{field}: "
                    f"expected {expected.required}, got {actual_required}"
                )
            if check_selectors:
                selector = getattr(actual_fields[field], "selector", "")
                if selector != expected.selector:
                    report.fail(
                        f"{label} selector mismatch for {service}.{field}: "
                        f"expected {expected.selector}, got {selector or '<missing>'}"
                    )


def _actual_required(value: ServiceFieldContract | bool) -> bool:
    """Return the required flag from either parsed layer."""
    if isinstance(value, ServiceFieldContract):
        return value.required
    return bool(value)
