"""Platform and option alignment verification."""

from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .constants import SOURCE_COMPONENT_ROOT
from .report import VerificationReport


def verify_platform_options_alignment(
    entries: Iterable[Mapping[str, Any]],
    entity_domain_counts: Mapping[str, int],
    report: VerificationReport,
) -> None:
    """Verify installed platform domains match config entry options."""
    entry_list = list(entries)
    if not entry_list:
        return

    contract = _installed_platform_contract()
    if contract is None:
        report.fail("platform constants are not literal")
        return
    platforms, experimental = contract
    if not platforms:
        report.fail("platform constants are empty")
        return
    if not experimental.issubset(platforms):
        report.fail(
            "experimental platforms are not declared platforms: "
            f"{sorted(experimental - platforms)}"
        )
        return

    expected_by_entry = [
        _enabled_platforms(entry.get("options"), platforms, experimental)
        for entry in entry_list
    ]
    expected_union = set().union(*expected_by_entry)
    actual_domains = {
        domain for domain, count in entity_domain_counts.items() if count > 0
    }
    unexpected_domains = sorted(actual_domains - expected_union)
    experimental_domains = sorted(actual_domains & (experimental - expected_union))

    if unexpected_domains:
        report.fail(
            "entity domains are not enabled by config entry options: "
            f"{unexpected_domains}"
        )
    if experimental_domains:
        report.fail(
            "experimental entity domains present without opt-in: "
            f"{experimental_domains}"
        )
    if not unexpected_domains and not experimental_domains:
        report.fact(
            "platform options alignment: "
            f"default_enabled={len(platforms - experimental)}, "
            f"experimental={sorted(experimental)}, "
            f"loaded_domains={sorted(actual_domains)}"
        )
    report.metric(
        "platform_options",
        {
            "actual_domains": sorted(actual_domains),
            "experimental": sorted(experimental),
            "expected_union": sorted(expected_union),
            "per_entry_expected_counts": sorted(
                Counter(len(platforms) for platforms in expected_by_entry).items()
            ),
        },
    )


def installed_enabled_platforms(options: Mapping[str, Any] | None = None) -> list[str]:
    """Return enabled platforms from installed literal constants."""
    contract = _installed_platform_contract()
    if contract is None:
        return []
    platforms, experimental = contract
    return sorted(_enabled_platforms(options, platforms, experimental))


def _enabled_platforms(
    options: object,
    platforms: set[str],
    experimental: set[str],
) -> set[str]:
    """Return enabled platform names for one installed config entry."""
    option_map = options if isinstance(options, Mapping) else {}
    if option_map.get("experimental_platforms", False) is True:
        return set(platforms)
    return platforms - experimental


def _installed_platform_contract() -> tuple[set[str], set[str]] | None:
    """Read installed platform constants without importing Home Assistant."""
    constants = _literal_module_lists(
        SOURCE_COMPONENT_ROOT / "const.py",
        {"PLATFORMS", "EXPERIMENTAL_PLATFORMS"},
    )
    platforms = constants.get("PLATFORMS")
    experimental = constants.get("EXPERIMENTAL_PLATFORMS")
    if platforms is None or experimental is None:
        return None
    return (set(platforms), set(experimental))


def _literal_module_lists(path: Path, names: set[str]) -> dict[str, list[str]]:
    """Return selected module-level string-list constants."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names:
                values[target.id] = value
    return values
