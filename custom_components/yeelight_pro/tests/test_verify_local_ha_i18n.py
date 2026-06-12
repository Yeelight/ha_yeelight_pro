"""Local HA installed i18n verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import VerificationReport, verify_i18n_contracts

from .i18n_helpers import translation_payload, write_installed_i18n


def test_verify_i18n_contracts_accepts_current_translation_boundary(
    tmp_path: Path,
) -> None:
    """i18n verifier 应接受当前安装态三份翻译和服务字段边界."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    write_installed_i18n(install_root)
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert report.ok
    assert any("i18n translations" in fact for fact in report.facts)
    metric = report.metrics["i18n_translations"]
    assert isinstance(metric, dict)
    assert metric["files"] == [
        "strings.json",
        "translations/en.json",
        "translations/zh-Hans.json",
    ]
    assert metric["service_fields"] == {
        "cleanup_registry": ["audit_id", "confirm", "entry_id"],
        "refresh": ["refresh_product_schemas"],
    }


def test_verify_i18n_contracts_rejects_leaf_key_drift(tmp_path: Path) -> None:
    """任一翻译文件少一个叶子 key 都应阻断本地 HA 验证."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    payload = translation_payload()
    del payload["options"]["step"]["general"]["data"]["debug_mode"]
    write_installed_i18n(install_root, english=payload)
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any("translation leaf paths mismatch" in failure for failure in report.failures)
    assert any("debug_mode" in failure for failure in report.failures)


def test_verify_i18n_contracts_rejects_options_under_config_path(
    tmp_path: Path,
) -> None:
    """options flow 翻译放在 config.options 时浏览器会显示原始字段名，必须阻断."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    payload = translation_payload()
    payload["config"]["options"] = payload.pop("options")
    write_installed_i18n(install_root, strings=payload, english=payload, chinese=payload)
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any("not config.options" in failure for failure in report.failures)
    assert any("options.step.general.data" in failure for failure in report.failures)


def test_verify_i18n_contracts_rejects_missing_required_service_translation(
    tmp_path: Path,
) -> None:
    """服务本身缺 name/description 翻译时应阻断 release 合同."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    payload = translation_payload()
    del payload["services"]["assign_areas"]["description"]
    write_installed_i18n(install_root, chinese=payload)
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any(
        "services.assign_areas.description" in failure
        for failure in report.failures
    )


def test_verify_i18n_contracts_rejects_unexpected_translated_service_field(
    tmp_path: Path,
) -> None:
    """翻译不存在于 services.yaml 的服务字段时应显式失败."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    payload = translation_payload()
    payload["services"]["refresh"]["fields"]["ghost_field"] = {
        "name": "Ghost",
        "description": "Unexpected translated field.",
    }
    write_installed_i18n(install_root, strings=payload, english=payload, chinese=payload)
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any(
        "i18n service field translations unexpected for refresh" in failure
        for failure in report.failures
    )
    assert any("ghost_field" in failure for failure in report.failures)


def test_verify_i18n_contracts_rejects_untranslated_option_schema_key(
    tmp_path: Path,
) -> None:
    """安装态 options schema 新增字段但未翻译时应阻断."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    write_installed_i18n(install_root, extra_option_key="future_option")
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any("future_option" in failure for failure in report.failures)


def test_verify_i18n_contracts_rejects_untranslated_selector_option(
    tmp_path: Path,
) -> None:
    """selector translation_key 的枚举值缺翻译时应阻断."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    payload = translation_payload()
    del payload["selector"]["device_import_filter_mode"]["options"]["and"]
    write_installed_i18n(install_root, strings=payload, english=payload, chinese=payload)
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any(
        "selector.device_import_filter_mode.options.and" in failure
        for failure in report.failures
    )


def test_verify_i18n_contracts_rejects_scan_login_guidance_drift(
    tmp_path: Path,
) -> None:
    """扫码登录翻译缺二维码、倒计时、轮询或刷新提示时应阻断."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    payload = translation_payload()
    payload["config"]["step"]["cloud_scan_login"]["description"] = (
        "Open Yeelight APP and scan the QR code. Status: {status}."
    )
    payload["config"]["progress"]["cloud_scan_login_wait"] = (
        "Waiting for scan authorization. Status: {status}."
    )
    write_installed_i18n(install_root, english=payload)
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any("Yeelight APP 1.5.0" in failure for failure in report.failures)
    assert any("refresh" in failure for failure in report.failures)
    assert any("qrcode" in failure for failure in report.failures)
    assert any("remaining_seconds" in failure for failure in report.failures)
    assert any("poll_count" in failure for failure in report.failures)


def test_verify_i18n_contracts_rejects_unknown_repair_placeholder(
    tmp_path: Path,
) -> None:
    """翻译文本引用 runtime 未提供的 Repairs 占位符时应阻断."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    payload = translation_payload()
    payload["issues"]["device_topology_changed"]["description"] += " {ghost}"
    write_installed_i18n(install_root, strings=payload, english=payload, chinese=payload)
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any("ghost" in failure for failure in report.failures)
    assert any("runtime placeholders missing" in failure for failure in report.failures)


def test_verify_i18n_contracts_rejects_untranslated_repair_placeholder(
    tmp_path: Path,
) -> None:
    """runtime 新增 Repairs 占位符但翻译未使用时应阻断."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    write_installed_i18n(install_root, extra_repair_placeholder="future")
    report = VerificationReport()

    verify_i18n_contracts(install_root, report)

    assert not report.ok
    assert any("future" in failure for failure in report.failures)
    assert any(
        "translation placeholders missing runtime keys" in failure
        for failure in report.failures
    )
