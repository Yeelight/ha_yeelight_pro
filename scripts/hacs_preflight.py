"""Local preflight checks for Yeelight Pro HACS readiness."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = ROOT / "custom_components" / "yeelight_pro"
sys.path.insert(0, str(ROOT))

from scripts.hacs_preflight_core import (  # noqa: E402
    check_exists,
    check_iot_registry_integrity,
    check_json,
    check_platform_constants,
    check_python_file_line_counts,
    check_readme_claims,
    check_release_quality_gates,
    check_user_visible_error_redaction,
)
from scripts.hacs_preflight_contracts import (  # noqa: E402
    check_forbidden_open_api_runtime,
    check_lan_contract_tests,
    check_push_contract_tests,
)
from scripts.hacs_preflight_diagnostics import check_diagnostics_contracts  # noqa: E402
from scripts.hacs_preflight_entity_filters import (  # noqa: E402
    check_dynamic_entity_filter_contracts,
)
from scripts.hacs_preflight_iot_registry_data import (  # noqa: E402
    IOT_REGISTRY_CONTRACT_TEST_TOKENS,
)
from scripts.hacs_preflight_local_ha import (  # noqa: E402
    VERIFY_LOCAL_HA_CONTRACT_TOKENS,
)
from scripts.hacs_preflight_lifecycle import check_lifecycle_contracts  # noqa: E402
from scripts.hacs_preflight_oauth_contracts import (  # noqa: E402
    check_oauth_contract_tests,
)
from scripts.hacs_preflight_runtime_options import (  # noqa: E402
    check_automation_contract_tests,
    check_runtime_options_contract_tests,
)
from scripts.hacs_preflight_split_contracts import (  # noqa: E402
    SPLIT_CONTRACT_TEST_TOKENS,
)


def _check_exists() -> list[str]:
    """Check required release-facing files."""
    return check_exists(ROOT)


def _check_json() -> list[str]:
    """Validate JSON syntax and required metadata fields."""
    return check_json(ROOT)


def _check_platform_constants() -> list[str]:
    """Check release platform claims against const.py."""
    return check_platform_constants(COMPONENT_ROOT)


def _check_python_file_line_counts() -> list[str]:
    """Keep Python files below the project line-count boundary."""
    return check_python_file_line_counts(ROOT)


def _check_release_quality_gates() -> list[str]:
    """Ensure local and CI release gates keep lint and type-check coverage."""
    return check_release_quality_gates(ROOT)


def _check_iot_registry_integrity() -> list[str]:
    """Check static Yeelight IoT registry invariants."""
    return check_iot_registry_integrity(COMPONENT_ROOT)


def _check_automation_contract_tests() -> list[str]:
    """Ensure release-sensitive entry points have tests."""
    return check_automation_contract_tests(COMPONENT_ROOT)


def _check_iot_registry_contract_tests() -> list[str]:
    """Ensure IoT registry and schema correction contracts stay tested."""
    errors: list[str] = []
    tests_root = COMPONENT_ROOT / "tests"
    for filename, required_tokens in IOT_REGISTRY_CONTRACT_TEST_TOKENS.items():
        path = tests_root / filename
        if not path.exists():
            errors.append(f"IoT registry contracts require tests/{filename}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"tests/{filename} missing {reason}: {token}")
    return errors


def _check_runtime_options_contract_tests() -> list[str]:
    """Ensure runtime-only options keep their selective reload contract."""
    return check_runtime_options_contract_tests(COMPONENT_ROOT)


def _check_split_contract_tests() -> list[str]:
    """Ensure split contract test files retain their release-sensitive coverage."""
    errors: list[str] = []
    for relative_path, required_tokens in SPLIT_CONTRACT_TEST_TOKENS.items():
        path = COMPONENT_ROOT / relative_path
        if not path.exists():
            errors.append(f"split contract tests require {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"{relative_path} missing {reason}: {token}")
    return errors


def _check_dynamic_entity_filter_contract_tests() -> list[str]:
    """Ensure runtime device import filtering remains non-destructive."""
    return check_dynamic_entity_filter_contracts(COMPONENT_ROOT)


def _check_lifecycle_contract_tests() -> list[str]:
    """Ensure HA registry lifecycle behavior remains covered before release."""
    return check_lifecycle_contracts(COMPONENT_ROOT)


def _check_push_contract_tests() -> list[str]:
    """Ensure push protocol contracts stay explicit before release."""
    return check_push_contract_tests(COMPONENT_ROOT)


def _check_oauth_contract_tests() -> list[str]:
    """Ensure OAuth protocol contracts stay explicit before release."""
    return check_oauth_contract_tests(COMPONENT_ROOT)


def _check_lan_contract_tests() -> list[str]:
    """Ensure LAN protocol contracts stay no-network and explicit."""
    return check_lan_contract_tests(COMPONENT_ROOT)


def _check_local_ha_verification_contract() -> list[str]:
    """Ensure the local HA validation gate keeps its safety checks."""
    errors: list[str] = []
    for relative_path, required_tokens in VERIFY_LOCAL_HA_CONTRACT_TOKENS.items():
        path = ROOT / relative_path
        if not path.exists():
            errors.append(f"local HA verification contract requires {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token, reason in required_tokens.items():
            if token not in content:
                errors.append(f"{relative_path} missing {reason}: {token}")
    return errors


def _check_diagnostics_redaction_contract_tests() -> list[str]:
    """Ensure diagnostics redaction and capability flags remain covered."""
    return check_diagnostics_contracts(COMPONENT_ROOT)


def _check_user_visible_error_redaction() -> list[str]:
    """Ensure HA user-visible errors do not interpolate raw runtime values."""
    return check_user_visible_error_redaction(COMPONENT_ROOT)


def _check_forbidden_open_api_runtime() -> list[str]:
    """Ensure destructive Open API endpoints stay out of runtime code."""
    return check_forbidden_open_api_runtime(COMPONENT_ROOT)


def _check_readme_claims() -> list[str]:
    """Block stale release claims in current release-facing docs."""
    return check_readme_claims(ROOT)


def _run_checks() -> list[tuple[str, list[str]]]:
    """Run all local HACS preflight checks."""
    return [
        ("required files", _check_exists()),
        ("JSON metadata", _check_json()),
        ("platform constants", _check_platform_constants()),
        ("Python file line counts", _check_python_file_line_counts()),
        ("release quality gates", _check_release_quality_gates()),
        ("IoT registry integrity", _check_iot_registry_integrity()),
        ("automation contract tests", _check_automation_contract_tests()),
        ("IoT registry contract tests", _check_iot_registry_contract_tests()),
        ("runtime options contract tests", _check_runtime_options_contract_tests()),
        ("split contract tests", _check_split_contract_tests()),
        (
            "dynamic entity filter contract tests",
            _check_dynamic_entity_filter_contract_tests(),
        ),
        ("lifecycle contract tests", _check_lifecycle_contract_tests()),
        (
            "diagnostics redaction contract tests",
            _check_diagnostics_redaction_contract_tests(),
        ),
        ("user-visible error redaction", _check_user_visible_error_redaction()),
        ("forbidden Open API runtime", _check_forbidden_open_api_runtime()),
        ("OAuth contract tests", _check_oauth_contract_tests()),
        ("push contract tests", _check_push_contract_tests()),
        ("LAN contract tests", _check_lan_contract_tests()),
        ("local HA verification contract", _check_local_ha_verification_contract()),
        ("release-facing claims", _check_readme_claims()),
    ]


def main() -> int:
    """CLI entrypoint."""
    print("Yeelight Pro local HACS preflight")
    print("=" * 40)

    failed = False
    for name, errors in _run_checks():
        if errors:
            failed = True
            print(f"[FAIL] {name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[OK] {name}")

    if failed:
        print("\nPreflight failed. Fix the items above before release review.")
        return 1

    print("\nPreflight passed. This is not publication approval.")
    print("Next required gates: pytest, hassfest, HACS action, release zip, local HA validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
