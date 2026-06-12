"""Platform candidate DEBUG logging regressions."""

from __future__ import annotations

import logging

from custom_components.yeelight_pro.capabilities.platform_contract import (
    platform_candidates_for_payload,
)


def test_platform_candidate_logging_reports_matched_property_evidence(caplog) -> None:
    """平台候选日志应说明由哪些属性证据产生，且不输出用户自定义名称."""
    payload = {
        "device_id": "contact-log-1",
        "name": "用户自定义门磁名称",
        "category": "contact_sensor",
        "type": "light",
        "params": {"dc": False, "alm": True, "bl": 75},
    }

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.capabilities.platform_contract_logging",
    ):
        assert platform_candidates_for_payload(payload) == ("binary_sensor", "sensor")

    assert "Resolved platform candidates" in caplog.text
    assert "device_id=contact-log-1" in caplog.text
    assert "category=contact_sensor" in caplog.text
    assert "candidates=('binary_sensor', 'sensor')" in caplog.text
    assert "read_only_bool_property" in caplog.text
    assert "read_only_sensor_property" in caplog.text
    assert "ignored=()" in caplog.text
    assert "用户自定义门磁名称" not in caplog.text


def test_platform_candidate_logging_reports_missing_capability_evidence(caplog) -> None:
    """category + 泛化 p 无候选时应留下稳定 reason，暴露证据不足."""
    payload = {
        "device_id": "light-power-only-log",
        "name": "用户自定义灯名",
        "category": "light",
        "params": {"p": True},
    }

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.capabilities.platform_contract_logging",
    ):
        assert platform_candidates_for_payload(payload) == ()

    assert "Resolved platform candidates" in caplog.text
    assert "device_id=light-power-only-log" in caplog.text
    assert "prop_ids=['p']" in caplog.text
    assert "candidates=()" in caplog.text
    assert "ignored=({'prop': 'p', 'reason': 'missing_light_capability_evidence'},)" in caplog.text
    assert "reason=missing_capability_evidence" in caplog.text
    assert "用户自定义灯名" not in caplog.text


def test_platform_candidate_logging_reports_ignored_unknown_property(caplog) -> None:
    """未知属性不生成实体时应留下原因，但不输出属性值或用户名称."""
    payload = {
        "device_id": "unknown-prop-log",
        "name": "用户自定义名称",
        "category": "other",
        "params": {"vendor_mode": "private"},
    }

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.capabilities.platform_contract_logging",
    ):
        assert platform_candidates_for_payload(payload) == ()

    assert "device_id=unknown-prop-log" in caplog.text
    assert "ignored=({'prop': 'vendor_mode', 'reason': 'unknown_property'},)" in caplog.text
    assert "private" not in caplog.text
    assert "用户自定义名称" not in caplog.text


def test_platform_candidate_logging_redacts_sensitive_property_keys(caplog) -> None:
    """平台候选日志不应输出 token/IP 等敏感 key 名或值."""
    payload = {
        "device_id": "sensitive-log",
        "category": "other",
        "params": {
            "access_token": "secret-token",
            "ip": "192.0.2.20",
            "vendor_mode": 1,
        },
    }

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.capabilities.platform_contract_logging",
    ):
        assert platform_candidates_for_payload(payload) == ()

    assert "prop_ids=['vendor_mode']" in caplog.text
    assert "vendor_mode" in caplog.text
    assert "access_token" not in caplog.text
    assert "secret-token" not in caplog.text
    assert "192.0.2.20" not in caplog.text
