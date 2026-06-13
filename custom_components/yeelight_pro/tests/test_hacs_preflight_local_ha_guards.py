"""Local HA preflight guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight
from scripts.hacs_preflight_local_ha import VERIFY_LOCAL_HA_CONTRACT_TOKENS
from scripts.hacs_preflight_local_ha_release import LOCAL_HA_RELEASE_CONTRACT_TOKENS
from scripts.hacs_preflight_local_ha_runtime import LOCAL_HA_RUNTIME_CONTRACT_TOKENS

from .hacs_preflight_local_ha_helpers import _write_local_ha_contract_fixture


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
        "scripts/hacs_preflight_local_ha_runtime_verifier_sources.py",
        "scripts/hacs_preflight_local_ha_runtime_verifier_storage.py",
        "scripts/hacs_preflight_local_ha_runtime_verifier_tests.py",
        "scripts/hacs_preflight_local_ha_protocol_contracts.py",
        "scripts/hacs_preflight_scan_login_contracts.py",
        "scripts/hacs_preflight_push_contracts.py",
        "scripts/hacs_preflight_local_ha_probes.py",
        "scripts/verify_push_websocket.py",
        "scripts/verify_scan_login.py",
        "scripts/verify_local_ha_recovery.py",
        "scripts/verify_local_ha_soak.py",
        "custom_components/yeelight_pro/tests/test_verify_scan_login.py",
        "custom_components/yeelight_pro/tests/test_verify_local_ha_recovery.py",
        "custom_components/yeelight_pro/tests/test_verify_local_ha_soak.py",
        "custom_components/yeelight_pro/tests/test_legacy_local_ha_entrypoints.py",
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
    assert any("destructive house transfer denylist" in error for error in errors)
    assert any("dangerous Open API runtime guard" in error for error in errors)
    assert any("house transfer endpoint runtime denylist" in error for error in errors)
    assert any("component release file group import" in error for error in errors)
    assert any("scan-login production test token guard" in error for error in errors)
    assert any("scan-login production probe script guard" in error for error in errors)
    assert any("scan-login HA-free contract path guard" in error for error in errors)
    assert any("platform constant release guard" in error for error in errors)
    assert any("Python source line-count release guard" in error for error in errors)
    assert any("release script command contract source" in error for error in errors)
    assert any("release script command guard" in error for error in errors)
    assert any("release-facing claim guard" in error for error in errors)
    assert any("required release file registry" in error for error in errors)
    assert any("legacy entrypoint token split coverage" in error for error in errors)
    assert any("manual HA smoke token split coverage" in error for error in errors)
    assert any(
        "production WebSocket probe script token guard" in error for error in errors
    )
    assert any("production WebSocket probe test token guard" in error for error in errors)
    assert any("production WebSocket confirm flag" in error for error in errors)
    assert any("production WebSocket token env guard" in error for error in errors)
    assert any("production WebSocket fail-closed guard" in error for error in errors)
    assert any("production WebSocket safe summary" in error for error in errors)
    assert any(
        "production WebSocket HA-free contract path" in error for error in errors
    )
    assert any(
        "production WebSocket HA-free contract loader" in error for error in errors
    )
    assert any("production WebSocket field-shape summary" in error for error in errors)
    assert any("production probe token registry" in error for error in errors)
    assert any("production scan-login probe script token guard" in error for error in errors)
    assert any("production scan-login probe test token guard" in error for error in errors)
    assert any("production scan-login confirm flag" in error for error in errors)
    assert any("production scan-login device env guard" in error for error in errors)
    assert any("production scan-login fail-closed guard" in error for error in errors)
    assert any("production scan-login safe summary" in error for error in errors)
    assert any(
        "production scan-login HA-free contract path" in error for error in errors
    )
    assert any(
        "production scan-login HA-free contract loader" in error for error in errors
    )
    assert any("production scan-login confirm guard coverage" in error for error in errors)
    assert any(
        "production scan-login device env guard coverage" in error
        for error in errors
    )
    assert any("production scan-login bounded-run guard coverage" in error for error in errors)
    assert any("production scan-login redacted summary coverage" in error for error in errors)
    assert any("production scan-login default no-network coverage" in error for error in errors)
    assert any(
        "production scan-login script-path no-network coverage" in error
        for error in errors
    )
    assert any("production scan-login fake-login aggregate coverage" in error for error in errors)
    assert any("dedicated local HA recovery script token guard" in error for error in errors)
    assert any("dedicated local HA recovery test token guard" in error for error in errors)
    assert any("dedicated recovery uses shared CLI" in error for error in errors)
    assert any("dedicated recovery repeat default token" in error for error in errors)
    assert any("dedicated recovery log-tail default token" in error for error in errors)
    assert any("dedicated recovery argv builder token" in error for error in errors)
    assert any("dedicated recovery Docker log guard token" in error for error in errors)
    assert any("dedicated recovery shared verifier token" in error for error in errors)
    assert any("dedicated local HA recovery default coverage" in error for error in errors)
    assert any(
        "dedicated local HA recovery docker-log guard coverage" in error
        for error in errors
    )
    assert any(
        "dedicated local HA recovery verifier reuse coverage" in error
        for error in errors
    )
    assert any(
        "dedicated local HA recovery script path coverage" in error
        for error in errors
    )
    assert any("dedicated local HA soak script token guard" in error for error in errors)
    assert any("dedicated local HA soak test token guard" in error for error in errors)
    assert any("dedicated soak uses shared CLI" in error for error in errors)
    assert any("dedicated soak default window token" in error for error in errors)
    assert any("dedicated soak default interval token" in error for error in errors)
    assert any("dedicated soak argv builder token" in error for error in errors)
    assert any("dedicated soak shared verifier token" in error for error in errors)
    assert any("dedicated local HA soak default coverage" in error for error in errors)
    assert any(
        "dedicated local HA soak verifier reuse coverage" in error for error in errors
    )
    assert any(
        "dedicated local HA soak script path coverage" in error for error in errors
    )
    assert any(
        "legacy actual-environment entrypoint delegates verifier" in error
        for error in errors
    )
    assert any(
        "legacy complete-HA entrypoint delegates verifier" in error
        for error in errors
    )
    assert any(
        "legacy functional entrypoint delegates verifier" in error
        for error in errors
    )
    assert any(
        "legacy real-HA entrypoint delegates verifier" in error for error in errors
    )
    assert any(
        "legacy local HA entrypoint verifier reuse coverage" in error
        for error in errors
    )
    assert any(
        "legacy local HA entrypoint script-path coverage" in error
        for error in errors
    )
    assert any("automation contract preflight helper" in error for error in errors)
    assert any("device trigger event payload fixture" in error for error in errors)
    assert any("matches Yeelight Pro runtime event bus payload" in error for error in errors)
    assert any("config-flow scan-login split test guard" in error for error in errors)
    assert any("P0 client helper split test guard" in error for error in errors)
    assert any("push payload split test guard" in error for error in errors)
    assert any("config-entry unload split test guard" in error for error in errors)
    assert any("explicit cleanup B confirm guard" in error for error in errors)
    assert any(
        "registry cleanup filtered-device confirm coverage" in error
        for error in errors
    )
    assert any(
        "filtered device stale-without-removal coverage" in error
        for error in errors
    )
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
    assert any("config entry unique-id isolation check" in error for error in errors)
    assert any("config entry expected unique-id helper" in error for error in errors)
    assert any("config entry unique-id stability metric" in error for error in errors)
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
    assert any(
        "runtime verifier source token registry" in error for error in errors
    )
    assert any("verify-local-ha source token coverage" in error for error in errors)
    assert any(
        "diagnostics verifier source token coverage" in error for error in errors
    )
    assert any("options-flow schema helper" in error for error in errors)
    assert any("config flow options helper" in error for error in errors)
    assert any(
        "sensor projector helper runtime module presence check" in error
        for error in errors
    )
    assert any(
        "node API list helper runtime module presence check" in error
        for error in errors
    )
    assert any(
        "node API property helper runtime module presence check" in error
        for error in errors
    )
    assert any("installed option_status field contract" in error for error in errors)
    assert any("installed option_status token contract" in error for error in errors)
    assert any("installed option_status verifier" in error for error in errors)
    assert any("installed option_status AST parser" in error for error in errors)
    assert any("installed option_status debug-mode guard" in error for error in errors)
    assert any("installed option_status scan-interval guard" in error for error in errors)
    assert any("option_status metric stability key" in error for error in errors)
    assert any(
        "installed diagnostic payload redaction token contract" in error
        for error in errors
    )
    assert any(
        "installed diagnostic payload redaction verifier" in error
        for error in errors
    )
    assert any(
        "installed diagnostic payload redaction AST parser" in error
        for error in errors
    )
    assert any("scan-login device redaction guard" in error for error in errors)
    assert any(
        "diagnostic payload redaction metric stability key" in error
        for error in errors
    )
    assert any("installed option_status field verifier coverage" in error for error in errors)
    assert any("installed option_status token verifier coverage" in error for error in errors)
    assert any("installed option_status normalization guard" in error for error in errors)
    assert any("installed option_status filter preview guard" in error for error in errors)
