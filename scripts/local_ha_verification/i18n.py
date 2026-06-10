"""Installed translation contract verification."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re
from typing import Any

from .constants import REQUIRED_SERVICES
from .i18n_payloads import (
    format_path,
    format_paths,
    leaf_paths,
    mapping_at,
    read_translation_payloads,
    value_at,
)
from .i18n_source import (
    installed_option_translation_keys,
    installed_repair_placeholder_keys,
    installed_selector_option_translation_paths,
)
from .report import VerificationReport
from .service_schema import documented_service_field_contracts

TRANSLATION_FILES = (
    "strings.json",
    "translations/en.json",
    "translations/zh-Hans.json",
)
SCAN_LOGIN_DESCRIPTION_PATH = (
    "config",
    "step",
    "cloud_scan_login",
    "description",
)
SCAN_LOGIN_PROGRESS_PATH = ("config", "progress", "cloud_scan_login_wait")
SCAN_LOGIN_PLACEHOLDERS = frozenset(
    {"qrcode", "status", "remaining_seconds", "poll_count"}
)
SCAN_LOGIN_PROGRESS_PLACEHOLDERS = frozenset(
    {"status", "remaining_seconds", "poll_count"}
)
SCAN_LOGIN_TEXT_MARKERS = {
    "strings.json": ("易来 APP 1.5.0", "刷新"),
    "translations/zh-Hans.json": ("易来 APP 1.5.0", "刷新"),
    "translations/en.json": ("Yeelight APP 1.5.0", "refresh"),
}

REQUIRED_I18N_LEAF_PATHS: set[tuple[str, ...]] = {
    ("config", "step", "user", "data", "connection_mode"),
    ("config", "step", "cloud_region", "data", "cloud_region"),
    ("config", "step", "cloud_auth", "data", "access_token"),
    ("config", "step", "cloud_auth_method", "data", "cloud_auth_method"),
    ("config", "step", "cloud_scan_login", "data", "scan_login_refresh"),
    ("config", "progress", "cloud_scan_login_wait"),
    ("config", "step", "cloud_houses", "data", "house_id"),
    (
        "config",
        "step",
        "cloud_devices",
        "data",
        "device_import_filter_include_devices",
    ),
    ("config", "step", "private_config", "data", "private_domain"),
    ("config", "step", "private_config", "data", "access_token"),
    ("config", "step", "private_config", "data", "house_id"),
    ("config", "step", "reauth_confirm", "data", "access_token"),
    ("config", "options", "step", "init", "data", "scan_interval"),
    ("config", "options", "step", "init", "data", "debug_mode"),
    ("config", "options", "step", "init", "data", "experimental_platforms"),
    ("config", "options", "step", "init", "data", "hide_unknown_entities"),
    ("config", "options", "step", "init", "data", "topology_change_repairs"),
    (
        "config",
        "options",
        "step",
        "init",
        "data",
        "device_import_filter_enabled",
    ),
    (
        "config",
        "options",
        "step",
        "init",
        "data",
        "device_import_filter_mode",
    ),
    ("config", "options", "step", "confirm_runtime", "title"),
    ("config", "options", "step", "confirm_runtime", "description"),
    ("config", "options", "step", "confirm_reload", "title"),
    ("config", "options", "step", "confirm_reload", "description"),
    ("config", "error", "cannot_connect"),
    ("config", "error", "invalid_auth"),
    ("config", "error", "unknown"),
    ("config", "abort", "already_configured"),
    ("config", "abort", "no_houses_found"),
    ("config", "abort", "reauth_successful"),
    ("issues", "device_topology_changed", "title"),
    ("issues", "device_topology_changed", "description"),
}


def verify_i18n_contracts(install_root: Path, report: VerificationReport) -> None:
    """Verify installed translation files stay aligned with public contracts."""
    services_path = install_root / "services.yaml"
    if not services_path.exists():
        report.fail("installed services.yaml is missing for i18n verification")
        return

    payloads = read_translation_payloads(install_root, TRANSLATION_FILES, report)
    if not payloads:
        return

    failure_count = len(report.failures)
    services_content = services_path.read_text(encoding="utf-8")
    service_fields = documented_service_field_contracts(services_content)

    _verify_leaf_paths(payloads, report)
    _verify_required_paths(
        payloads,
        installed_option_translation_keys(install_root),
        installed_selector_option_translation_paths(install_root),
        report,
    )
    _verify_service_translations(payloads, service_fields, report)
    _verify_repair_placeholders(install_root, payloads, report)
    _verify_scan_login_translation_guidance(payloads, report)

    if len(report.failures) == failure_count:
        leaf_count = len(leaf_paths(next(iter(payloads.values()))))
        translated_fields = _translated_service_fields(next(iter(payloads.values())))
        report.fact(
            "i18n translations: "
            f"{len(payloads)} files, {leaf_count} leaf paths, "
            f"services={len(REQUIRED_SERVICES)}, "
            f"service_fields={sum(len(fields) for fields in translated_fields.values())}"
        )
    report.metric(
        "i18n_translations",
        {
            "files": sorted(payloads),
            "leaf_paths": len(leaf_paths(next(iter(payloads.values())))),
            "service_fields": {
                service: sorted(fields)
                for service, fields in sorted(
                    _translated_service_fields(next(iter(payloads.values()))).items()
                )
            },
        },
    )


def _verify_leaf_paths(
    payloads: Mapping[str, dict[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify all installed translation files expose the same leaf keys."""
    baseline_name, baseline_payload = next(iter(payloads.items()))
    baseline = leaf_paths(baseline_payload)
    for name, payload in payloads.items():
        paths = leaf_paths(payload)
        missing = sorted(baseline - paths)
        unexpected = sorted(paths - baseline)
        if missing:
            report.fail(
                f"translation leaf paths mismatch for {name}; "
                f"missing vs {baseline_name}: {format_paths(missing)}"
            )
        if unexpected:
            report.fail(
                f"translation leaf paths mismatch for {name}; "
                f"unexpected vs {baseline_name}: {format_paths(unexpected)}"
            )


def _verify_required_paths(
    payloads: Mapping[str, dict[str, Any]],
    option_keys: set[str],
    selector_option_paths: set[tuple[str, ...]],
    report: VerificationReport,
) -> None:
    """Verify required config/options/service paths remain translated."""
    required_paths = set(REQUIRED_I18N_LEAF_PATHS)
    required_paths.update(selector_option_paths)
    for option_key in option_keys:
        required_paths.add(("config", "options", "step", "init", "data", option_key))
    for service in REQUIRED_SERVICES:
        required_paths.add(("services", service, "name"))
        required_paths.add(("services", service, "description"))

    for name, payload in payloads.items():
        paths = leaf_paths(payload)
        missing = sorted(required_paths - paths)
        for path in missing:
            report.fail(f"i18n required path missing in {name}: {format_path(path)}")


def _verify_service_translations(
    payloads: Mapping[str, dict[str, Any]],
    documented_fields: Mapping[str, Mapping[str, object]],
    report: VerificationReport,
) -> None:
    """Verify service and translated-field keys match the installed services.yaml."""
    expected_services = set(REQUIRED_SERVICES)
    baseline_name, baseline_payload = next(iter(payloads.items()))
    baseline_fields = _translated_service_fields(baseline_payload)

    for name, payload in payloads.items():
        services = mapping_at(payload, ("services",))
        actual_services = set(services)
        missing_services = sorted(expected_services - actual_services)
        unexpected_services = sorted(actual_services - expected_services)
        if missing_services:
            report.fail(f"i18n service translations missing in {name}: {missing_services}")
        if unexpected_services:
            report.fail(
                f"i18n service translations unexpected in {name}: {unexpected_services}"
            )

        fields = _translated_service_fields(payload)
        if fields != baseline_fields:
            report.fail(
                f"i18n service field translations mismatch for {name} "
                f"vs {baseline_name}: {fields}"
            )
        for service, translated_fields in sorted(fields.items()):
            documented = set(documented_fields.get(service, {}))
            unexpected_fields = sorted(translated_fields - documented)
            if unexpected_fields:
                report.fail(
                    "i18n service field translations unexpected for "
                    f"{service} in {name}: {unexpected_fields}"
                )
            for field in sorted(translated_fields):
                field_translation = mapping_at(
                    payload,
                    ("services", service, "fields", field),
                )
                missing_leafs = {"name", "description"} - set(field_translation)
                if missing_leafs:
                    report.fail(
                        "i18n service field translation incomplete for "
                        f"{service}.{field} in {name}: {sorted(missing_leafs)}"
                    )


def _translated_service_fields(payload: Mapping[str, Any]) -> dict[str, set[str]]:
    """Return translated service field keys by service."""
    result: dict[str, set[str]] = {}
    services = mapping_at(payload, ("services",))
    for service in REQUIRED_SERVICES:
        fields = mapping_at(services, (service, "fields"))
        if fields:
            result[service] = set(fields)
    return result


def _verify_repair_placeholders(
    install_root: Path,
    payloads: Mapping[str, dict[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify Repairs translation placeholders match runtime placeholders."""
    runtime_placeholders = installed_repair_placeholder_keys(install_root)
    if not runtime_placeholders:
        report.fail("repair issue runtime placeholders missing for device_topology_changed")
        return

    for name, payload in payloads.items():
        description = value_at(
            payload,
            ("issues", "device_topology_changed", "description"),
        )
        if not isinstance(description, str):
            report.fail(
                "repair issue translation description missing in "
                f"{name}: device_topology_changed"
            )
            continue
        translated_placeholders = set(re.findall(r"{([^{}]+)}", description))
        missing_runtime = sorted(translated_placeholders - runtime_placeholders)
        missing_translation = sorted(runtime_placeholders - translated_placeholders)
        if missing_runtime:
            report.fail(
                "repair issue runtime placeholders missing keys used by "
                f"{name}: {missing_runtime}"
            )
        if missing_translation:
            report.fail(
                "repair issue translation placeholders missing runtime keys in "
                f"{name}: {missing_translation}"
            )


def _verify_scan_login_translation_guidance(
    payloads: Mapping[str, dict[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify scan-login QR guidance keeps countdown and refresh details."""
    for name, payload in payloads.items():
        description = value_at(payload, SCAN_LOGIN_DESCRIPTION_PATH)
        progress = value_at(payload, SCAN_LOGIN_PROGRESS_PATH)
        if not isinstance(description, str):
            report.fail(
                "scan-login QR description missing in "
                f"{name}: {format_path(SCAN_LOGIN_DESCRIPTION_PATH)}"
            )
            continue
        if not isinstance(progress, str):
            report.fail(
                "scan-login QR progress text missing in "
                f"{name}: {format_path(SCAN_LOGIN_PROGRESS_PATH)}"
            )
            continue

        markers = SCAN_LOGIN_TEXT_MARKERS.get(name, ())
        _verify_text_markers(
            name,
            description,
            markers,
            "scan-login QR description",
            report,
        )
        _verify_placeholders(
            name,
            description,
            SCAN_LOGIN_PLACEHOLDERS,
            "scan-login QR description",
            report,
        )
        _verify_placeholders(
            name,
            progress,
            SCAN_LOGIN_PROGRESS_PLACEHOLDERS,
            "scan-login QR progress text",
            report,
        )


def _verify_text_markers(
    name: str,
    text: str,
    markers: tuple[str, ...],
    label: str,
    report: VerificationReport,
) -> None:
    """Verify required UX markers remain present in one translated text."""
    folded_text = text.casefold()
    for marker in markers:
        if marker.casefold() not in folded_text:
            report.fail(f"{label} missing marker in {name}: {marker}")


def _verify_placeholders(
    name: str,
    text: str,
    required: frozenset[str],
    label: str,
    report: VerificationReport,
) -> None:
    """Verify a translated text keeps all required placeholders."""
    placeholders = set(re.findall(r"{([^{}]+)}", text))
    missing = sorted(required - placeholders)
    if missing:
        report.fail(f"{label} missing placeholders in {name}: {missing}")
