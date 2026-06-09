"""Local HA preflight guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight
from scripts.hacs_preflight_local_ha import VERIFY_LOCAL_HA_CONTRACT_TOKENS
from scripts.hacs_preflight_local_ha_release import LOCAL_HA_RELEASE_CONTRACT_TOKENS
from scripts.hacs_preflight_local_ha_runtime import LOCAL_HA_RUNTIME_CONTRACT_TOKENS


def test_local_ha_contract_tokens_are_split_by_release_and_runtime() -> None:
    """本地 HA 合同 token 必须保留 release/runtime 分层聚合."""
    assert VERIFY_LOCAL_HA_CONTRACT_TOKENS == {
        **LOCAL_HA_RELEASE_CONTRACT_TOKENS,
        **LOCAL_HA_RUNTIME_CONTRACT_TOKENS,
    }
    assert {
        "scripts/hacs_preflight_local_ha_release.py",
        "scripts/hacs_preflight_local_ha_runtime.py",
        "scripts/hacs_preflight_local_ha_runtime_core_tests.py",
        "scripts/hacs_preflight_local_ha_runtime_sources.py",
        "scripts/hacs_preflight_local_ha_runtime_tests.py",
        "scripts/hacs_preflight_local_ha_runtime_verifier_tests.py",
        "scripts/hacs_preflight_push_contracts.py",
    } <= VERIFY_LOCAL_HA_CONTRACT_TOKENS.keys()


def test_local_ha_verification_contract_requires_safety_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝被削弱的本地 HA 验证脚本."""
    root = tmp_path
    scripts_root = root / "scripts"
    local_ha_root = scripts_root / "local_ha_verification"
    tests_root = root / "custom_components" / "yeelight_pro" / "tests"
    scripts_root.mkdir(parents=True)
    local_ha_root.mkdir()
    tests_root.mkdir(parents=True)
    _write_local_ha_contract_fixture(scripts_root, local_ha_root, tests_root)
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_local_ha_verification_contract()

    assert any("release-excluded install artifact check" in error for error in errors)
    assert any("product schema privacy scan" in error for error in errors)
    assert any("schema cache privacy coverage" in error for error in errors)
    assert any("stale regex release claim guard data" in error for error in errors)
    assert any("unverified OAuth claim denylist" in error for error in errors)
    assert any("overstated analytics runtime claim denylist" in error for error in errors)
    assert any("destructive house transfer denylist" in error for error in errors)
    assert any("dangerous Open API runtime guard" in error for error in errors)
    assert any("house transfer endpoint runtime denylist" in error for error in errors)
    assert any("analytics contract zip required file guard" in error for error in errors)
    assert any("platform constant release guard" in error for error in errors)
    assert any("Python source line-count release guard" in error for error in errors)
    assert any("release script command contract source" in error for error in errors)
    assert any("release script command guard" in error for error in errors)
    assert any("release-facing claim guard" in error for error in errors)
    assert any("required release file registry" in error for error in errors)
    assert any("automation contract preflight helper" in error for error in errors)
    assert any("device trigger event payload fixture" in error for error in errors)
    assert any("matches Yeelight Pro runtime event bus payload" in error for error in errors)
    assert any("config-flow OAuth split test guard" in error for error in errors)
    assert any("P0 client helper split test guard" in error for error in errors)
    assert any("push payload split test guard" in error for error in errors)
    assert any("config-entry unload split test guard" in error for error in errors)
    assert any("explicit cleanup B confirm guard" in error for error in errors)
    assert any("device removal fail-closed guard" in error for error in errors)
    assert any("release quality gate drift coverage" in error for error in errors)
    assert any("missing release script coverage" in error for error in errors)
    assert any("dynamic CHECKS rejection coverage" in error for error in errors)
    assert any("stored import filter migration" in error for error in errors)
    assert any("canonical filter storage helper" in error for error in errors)
    assert any("form-only filter cleanup coverage" in error for error in errors)
    assert any("state-only topology generation coverage" in error for error in errors)
    assert any("removed device topology diff coverage" in error for error in errors)
    assert any("schema cache object-shape guard" in error for error in errors)
    assert any("schema cache JSON-safe object guard" in error for error in errors)
    assert any("schema cache object-shape coverage" in error for error in errors)
    assert any("schema cache sensitive-key denylist" in error for error in errors)
    assert any("schema cache sensitive-value denylist" in error for error in errors)
    assert any("schema cache source privacy coverage" in error for error in errors)
    assert any("schema cache fetch log redaction coverage" in error for error in errors)
    assert any(
        "spec correction normalizer runtime module presence check" in error
        for error in errors
    )
    assert any("runtime inference helper module presence check" in error for error in errors)
    assert any("options flow helper zip required file guard" in error for error in errors)
    assert any("options-flow schema helper" in error for error in errors)
    assert any("config flow options helper" in error for error in errors)
    assert any("sensor projector helper runtime module presence check" in error for error in errors)
    assert any("node API list helper runtime module presence check" in error for error in errors)
    assert any("node API property helper runtime module presence check" in error for error in errors)
    assert any("installed option_status field contract" in error for error in errors)
    assert any("installed option_status token contract" in error for error in errors)
    assert any("installed option_status verifier" in error for error in errors)
    assert any("installed option_status AST parser" in error for error in errors)
    assert any("installed option_status debug-mode guard" in error for error in errors)
    assert any("installed option_status scan-interval guard" in error for error in errors)
    assert any("option_status metric stability key" in error for error in errors)
    assert any("installed option_status field verifier coverage" in error for error in errors)
    assert any("installed option_status token verifier coverage" in error for error in errors)
    assert any("installed option_status normalization guard" in error for error in errors)
    assert any("installed option_status filter preview guard" in error for error in errors)


def _write_local_ha_contract_fixture(
    scripts_root: Path,
    local_ha_root: Path,
    tests_root: Path,
) -> None:
    """Write an intentionally weakened local-HA contract fixture."""
    _write_test_file(
        scripts_root / "verify_local_ha.py",
        "scripts.local_ha_verification.cli",
    )
    _write_test_file(local_ha_root / "install.py", "runtime_diff")
    _write_test_file(local_ha_root / "storage.py", "verify_storage")
    _write_test_file(local_ha_root / "services.py", "verify_services")
    _write_test_file(local_ha_root / "runtime.py", "verify_logs")
    _write_test_file(
        local_ha_root / "diagnostics.py",
        (
            "DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES "
            "DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES "
            "DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES "
            "verify_diagnostics_capabilities diagnostics_capabilities"
        ),
    )
    _write_test_file(local_ha_root / "constants.py", "BAD_LOG_MARKERS")
    _write_test_file(local_ha_root / "cli.py", "build_parser")
    _write_test_file(scripts_root / "check_release_zip.py", "REQUIRED_FILES")
    _write_test_file(scripts_root / "hacs_preflight_claims.py", "STALE_DOC_CLAIMS")
    _write_test_file(scripts_root / "hacs_preflight_release_files.py", "")
    _write_test_file(
        scripts_root / "hacs_preflight_local_ha_release.py",
        (
            "LOCAL_HA_RELEASE_CONTRACT_TOKENS "
            "hacs_preflight_claims.py "
            "hacs_preflight_core.py "
            "hacs_preflight_split_contracts.py "
            "hacs_preflight_release_files.py "
            "hacs_preflight_lifecycle.py "
            "hacs_preflight_push_contracts.py "
            "hacs_preflight_local_ha_runtime_sources.py "
            "hacs_preflight_local_ha_runtime_core_tests.py "
            "hacs_preflight_local_ha_runtime_tests.py "
            "hacs_preflight_local_ha_runtime_verifier_tests.py"
        ),
    )
    _write_test_file(
        scripts_root / "hacs_preflight_contracts.py",
        "check_push_contract_tests",
    )
    _write_test_file(
        scripts_root / "hacs_preflight_push_contracts.py",
        "PUSH_CONTRACT_REQUIRED_FILES",
    )
    _write_test_file(scripts_root / "hacs_preflight_runtime_options.py", "")
    _write_test_file(scripts_root / "hacs_preflight_core.py", "check_exists")
    _write_test_file(
        scripts_root / "hacs_preflight_split_contracts.py",
        (
            "SPLIT_CONTRACT_TEST_TOKENS "
            "test_capability_registry_contract.py "
            "test_options_flow_contract.py "
            "test_translation_runtime_contract.py"
        ),
    )
    _write_test_file(
        scripts_root / "hacs_preflight_lifecycle.py",
        "LIFECYCLE_CONTRACT_TOKENS async_remove_config_entry_device",
    )
    _write_test_file(tests_root / "test_verify_local_ha.py", "runtime_diff")
    _write_test_file(tests_root / "test_verify_local_ha_runtime.py", "verify_logs")
    _write_test_file(tests_root / "test_verify_local_ha_storage.py", "verify_storage")
    _write_test_file(
        tests_root / "test_verify_local_ha_diagnostics.py",
        (
            "test_verify_diagnostics_capabilities_accepts_release_boundaries "
            "test_verify_diagnostics_capabilities_rejects_enabled_live_flag "
            "test_verify_diagnostics_capabilities_rejects_ambiguous_oauth_flow_flag "
            "test_verify_diagnostics_capabilities_requires_literal_flags"
        ),
    )
    _write_test_file(tests_root / "test_verify_local_ha_schema_cache.py", "")
    _write_test_file(tests_root / "test_schema_cache.py", "")
    _write_test_file(tests_root / "test_schema_cache_logging.py", "")
    _write_test_file(tests_root / "test_coordinator_topology.py", "")
    _write_test_file(tests_root / "test_coordinator_topology_diff.py", "")
    _write_test_file(tests_root / "test_hacs_preflight_release_quality.py", "")
    _write_test_file(tests_root / "test_hacs_preflight_runtime_options.py", "")
    _write_test_file(tests_root.parent / "entry_migration.py", "")
    _write_test_file(tests_root.parent / "device_filter.py", "")
    _write_test_file(tests_root.parent / "config_flow_helpers.py", "")
    _write_test_file(tests_root.parent / "config_flow_options.py", "")
    (tests_root.parent / "core").mkdir()
    _write_test_file(tests_root.parent / "core" / "schema_cache.py", "")
    _write_test_file(tests_root / "test_entry_migration.py", "")
    _write_test_file(tests_root / "test_entry_options_migration.py", "")


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
