"""Release-facing documentation claim guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_gap_review_is_scanned_for_stale_release_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ha_xiaomi_home gap review 必须纳入 release-facing claim guard."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "HA_XIAOMI_HOME_GAP_REVIEW.md",
        "live WebSocket is implemented",
    )
    _write_test_file(docs_root / "IOT_SPEC_REGISTRY.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert (
        "stale release claim in docs/HA_XIAOMI_HOME_GAP_REVIEW.md: "
        "live WebSocket is implemented"
    ) in errors


def test_all_top_level_docs_are_scanned_for_stale_release_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """所有 release-facing docs/*.md 都必须纳入声明漂移扫描."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "PROJECT_SUMMARY.md", "OAuth 已实现")
    _write_test_file(iot_root / "易来照明系统开放平台.md", "OAuth 已实现")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert (
        "stale release claim in docs/PROJECT_SUMMARY.md: OAuth 已实现"
    ) in errors
    assert all("docs/iot" not in error for error in errors)


def test_release_claim_guard_rejects_new_fixed_test_and_zip_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能固定宣传新的测试数量、文件数或覆盖率."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "686 passed\n102 files\n80%")
    _write_test_file(root / "README_zh.md", "通过 686 个测试")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "TEST_REPORT.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: /\\d+\\s+passed/" in error for error in errors)
    assert any("README.md: /\\d+\\s+files/" in error for error in errors)
    assert any("README.md: /\\d+\\s*%/" in error for error in errors)
    assert any(
        "README_zh.md: /(?:通过|共)\\s*\\d+\\s*个测试/" in error
        for error in errors
    )


def test_release_claim_guard_rejects_direct_component_copy_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能回退到复制整个组件目录的安装方式."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "cp -R custom_components/yeelight_pro")
    _write_test_file(root / "README_zh.md", "cp -r custom_components/yeelight_pro")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "TEST_REPORT.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md" in error for error in errors)
    assert any("README_zh.md" in error for error in errors)


def test_release_claim_guard_rejects_house_transfer_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能把家庭转移危险接口声明为已支持."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "house transfer is implemented")
    _write_test_file(root / "README_zh.md", "家庭转移已支持")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "RELEASE_STATUS.md", "")
    _write_test_file(iot_root / "易来照明系统开放平台.md", "家庭转移已支持")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: house transfer is implemented" in error for error in errors)
    assert any("README_zh.md: 家庭转移已支持" in error for error in errors)
    assert all("docs/iot" not in error for error in errors)

def test_release_claim_guard_rejects_obsolete_sse_runtime_gap_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能把实时事件边界回退成 WebSocket/SSE 混写."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "TEST_REPORT.md",
        "WebSocket / SSE / subscription 尚未作为运行时能力完成",
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any(
        "docs/TEST_REPORT.md: WebSocket / SSE / subscription 尚未作为运行时能力完成"
        in error
        for error in errors
    )


def test_release_claim_guard_rejects_websocket_sse_mixed_live_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能重新把易来实时事件写成 WebSocket/SSE 混合能力."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "live WebSocket or SSE runtime")
    _write_test_file(root / "README_zh.md", "SSE 事件通知已支持")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(iot_root / "易来照明系统开放平台.md", "WebSocket/SSE")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: /WebSocket\\s*(?:or|and|\\+)\\s*SSE/" in error for error in errors)
    assert any("README_zh.md: /SSE.{0,20}" in error for error in errors)
    assert all("docs/iot" not in error for error in errors)


def test_release_claim_guard_rejects_eventsource_live_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能把实时事件写成 EventSource/SSE."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "EventSource live runtime")
    _write_test_file(root / "README_zh.md", "Server-Sent Events runtime")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "TEST_REPORT.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: EventSource" in error for error in errors)
    assert any("README_zh.md: Server-Sent Events" in error for error in errors)


def test_release_claim_guard_rejects_obsolete_oauth_decision_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能再把 HA OAuth 取舍写成当前决策阻塞项."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "HA_XIAOMI_HOME_GAP_REVIEW.md",
        "Home Assistant OAuth product approval",
    )
    _write_test_file(
        docs_root / "MIGRATION_PLAN.md",
        "Home Assistant OAuth 取舍",
    )
    _write_test_file(
        docs_root / "PROJECT_SUMMARY.md",
        "Home Assistant OAuth 登录是否仍作为扫码登录之外的目标",
    )
    _write_test_file(iot_root / "易来照明系统开放平台.md", "Home Assistant OAuth 取舍")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("docs/HA_XIAOMI_HOME_GAP_REVIEW.md" in error for error in errors)
    assert any("docs/MIGRATION_PLAN.md: Home Assistant OAuth 取舍" in error for error in errors)
    assert any(
        "docs/PROJECT_SUMMARY.md: Home Assistant OAuth 登录是否仍作为扫码登录之外的目标"
        in error
        for error in errors
    )
    assert all("docs/iot" not in error for error in errors)


def test_release_claim_guard_rejects_device_picker_blocking_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能回退为设备列表失败阻断配置."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(
        root / "README.md",
        "device picker requires the device list before setup can continue",
    )
    _write_test_file(
        root / "README_zh.md",
        "设备 picker 必须加载设备列表才能继续配置",
    )
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "PROJECT_SUMMARY.md",
        "device list load failure blocks configuration",
    )
    _write_test_file(
        iot_root / "易来照明系统开放平台.md",
        "设备列表加载失败会阻止配置",
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md" in error and "device picker" in error for error in errors)
    assert any("README_zh.md" in error and "设备 picker" in error for error in errors)
    assert any(
        "docs/PROJECT_SUMMARY.md: device list load failure blocks configuration"
        in error
        for error in errors
    )
    assert all("docs/iot" not in error for error in errors)


def test_release_claim_guard_rejects_overstated_gateway_discovery_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能把 UDP fallback 夸大成 mDNS 或默认发现."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "mDNS discovery is implemented")
    _write_test_file(root / "README_zh.md", "本地网关发现默认启用")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "PROJECT_SUMMARY.md",
        "automatic local gateway discovery is implemented",
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: mDNS discovery is implemented" in error for error in errors)
    assert any("README_zh.md: 本地网关发现默认启用" in error for error in errors)
    assert any(
        "docs/PROJECT_SUMMARY.md: automatic local gateway discovery is implemented"
        in error
        for error in errors
    )


def test_release_claim_guard_rejects_obsolete_local_ha_incomplete_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能回退为本地 HA 验证闭环未完成旧口径."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "local HA validation is incomplete")
    _write_test_file(root / "README_zh.md", "本地 HA 实测未完成")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "MIGRATION_PLAN.md",
        "补足本地 Home Assistant 实测闭环",
    )
    _write_test_file(iot_root / "易来照明系统开放平台.md", "本地 HA 实测未完成")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: local HA validation is incomplete" in error for error in errors)
    assert any("README_zh.md: 本地 HA 实测未完成" in error for error in errors)
    assert any(
        "docs/MIGRATION_PLAN.md: 补足本地 Home Assistant 实测闭环" in error
        for error in errors
    )
    assert all("docs/iot" not in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
