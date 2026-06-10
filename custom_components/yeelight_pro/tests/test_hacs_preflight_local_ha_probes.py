"""Local HA preflight guard tests for production probe scripts."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight
from scripts.hacs_preflight_local_ha import VERIFY_LOCAL_HA_CONTRACT_TOKENS

from .hacs_preflight_local_ha_helpers import _write_local_ha_contract_fixture


def test_local_ha_contract_tokens_include_cloud_devices_probe() -> None:
    """生产探针必须进入本地 HA 合同 token 聚合."""
    assert {
        "scripts/verify_analytics.py",
        "scripts/verify_cloud_devices.py",
        "scripts/verify_lan_gateway.py",
        "custom_components/yeelight_pro/tests/test_verify_analytics.py",
        "custom_components/yeelight_pro/tests/test_verify_cloud_devices.py",
        "custom_components/yeelight_pro/tests/test_verify_lan_gateway.py",
    } <= VERIFY_LOCAL_HA_CONTRACT_TOKENS.keys()


def test_local_ha_contract_requires_cloud_devices_probe_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝削弱云端真实设备 picker 生产探针的安全边界."""
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

    assert any("production cloud devices probe script token guard" in error for error in errors)
    assert any("production cloud devices probe test token guard" in error for error in errors)
    assert any("production cloud devices confirm flag" in error for error in errors)
    assert any("production cloud devices token env guard" in error for error in errors)
    assert any("production cloud devices house env guard" in error for error in errors)
    assert any("production cloud devices fail-closed guard" in error for error in errors)
    assert any("production cloud devices safe summary" in error for error in errors)
    assert any("production cloud devices client loader" in error for error in errors)
    assert any("production cloud devices aggregate-only summary" in error for error in errors)
    assert any("production cloud devices category-count summary" in error for error in errors)


def test_local_ha_contract_requires_lan_gateway_probe_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝削弱 LAN 网关生产探针的安全边界."""
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

    assert any("production LAN gateway probe script token guard" in error for error in errors)
    assert any("production LAN gateway probe test token guard" in error for error in errors)


def test_local_ha_contract_requires_analytics_probe_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝削弱 analytics 生产探针的安全边界."""
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

    assert any("production analytics probe script token guard" in error for error in errors)
    assert any("production analytics probe test token guard" in error for error in errors)
    assert any("production analytics confirm flag" in error for error in errors)
    assert any("production analytics token env guard" in error for error in errors)
    assert any("production analytics house env guard" in error for error in errors)
    assert any("production analytics fail-closed guard" in error for error in errors)
    assert any("production analytics safe summary" in error for error in errors)
    assert any("production analytics field-shape summary" in error for error in errors)
    assert any("production analytics numeric-field summary" in error for error in errors)
    assert any("production analytics confirm guard coverage" in error for error in errors)
    assert any("production analytics env guard coverage" in error for error in errors)
    assert any(
        "production analytics bounded-request guard coverage" in error
        for error in errors
    )
    assert any("production analytics raw payload redaction coverage" in error for error in errors)
    assert any("production analytics default no-network coverage" in error for error in errors)
    assert any(
        "production analytics script-path no-network coverage" in error
        for error in errors
    )
    assert any(
        "production analytics fake-payload aggregate coverage" in error
        for error in errors
    )
    assert any("production cloud devices confirm guard coverage" in error for error in errors)
    assert any("production cloud devices token env guard coverage" in error for error in errors)
    assert any("production cloud devices house env guard coverage" in error for error in errors)
    assert any("production cloud devices bounded-run guard coverage" in error for error in errors)
    assert any("production cloud devices redacted summary coverage" in error for error in errors)
    assert any("production cloud devices default no-network coverage" in error for error in errors)
    assert any(
        "production cloud devices script-path no-network coverage" in error
        for error in errors
    )
    assert any("production cloud devices fake-device aggregate coverage" in error for error in errors)
