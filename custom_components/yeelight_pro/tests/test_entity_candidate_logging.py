"""Entity candidate debug logging tests."""

from __future__ import annotations

import logging

from custom_components.yeelight_pro.entity_candidates import iter_entity_candidates

from .test_entity_candidates import _Coordinator, _light_payload
from .test_entity_candidate_device_sections import _schema_rich_light_payload


def test_entity_candidate_logging_reports_projected_domain_summary(
    caplog,
) -> None:
    """候选日志应暴露每台设备的 domain 聚合，不输出 raw payload."""
    payload = _light_payload()
    payload["online"] = False
    payload["ha_device_instance"]["online"] = False
    coordinator = _Coordinator(data={"light": payload})

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.entity_candidates",
    ):
        candidates = list(iter_entity_candidates(coordinator))

    assert [(item.platform, item.available) for item in candidates] == [
        ("light", False)
    ]
    assert (
        "Projected Yeelight Pro device entity candidates: device_id=light-1 "
        "category=light type=light total=1 domains={'light': 1} "
        "sections={'control': 1} "
        "unavailable_domains={'light': 1}"
    ) in caplog.text
    assert "component_count=1" in caplog.text
    assert "prop_count=2" in caplog.text
    assert "prop_ids=('l', 'p')" in caplog.text
    assert "event_count=0" in caplog.text
    assert "reason=projected_candidates" in caplog.text
    assert "ha_device_instance" not in caplog.text


def test_entity_candidate_logging_reports_filter_skip(caplog) -> None:
    """设备 picker 排除时应给出稳定 reason code，便于排查缺实体."""
    payload = _light_payload()
    coordinator = _Coordinator(
        data={"blocked": payload},
        options={
            "device_import_filter": {
                "enabled": True,
                "exclude": {"devices": ["light-1"]},
            }
        },
    )

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.entity_candidates",
    ):
        candidates = list(iter_entity_candidates(coordinator))

    assert candidates == []
    assert (
        "Skipping Yeelight Pro device entity candidates: device_id=light-1 "
        "category=light type=light reason=device_import_filter_excluded"
    ) in caplog.text


def test_entity_candidate_logging_reports_device_page_sections(caplog) -> None:
    """候选日志应暴露 HA 设备页 section 聚合，便于排查是否只有控制项."""
    payload = _schema_rich_light_payload()
    payload["name"] = "用户自定义多能力设备"
    coordinator = _Coordinator(data={"rich": payload})

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.entity_candidates",
    ):
        candidates = list(iter_entity_candidates(coordinator))

    assert candidates
    assert "device_id=rich-light-1" in caplog.text
    assert (
        "sections={'config': 3, 'control': 1, 'diagnostic': 1, "
        "'event': 1, 'sensor': 1}"
    ) in caplog.text
    assert "component_count=1" in caplog.text
    assert "component_categories=('color temperature light',)" in caplog.text
    assert "event_count=2" in caplog.text
    assert "用户自定义多能力设备" not in caplog.text


def test_entity_candidate_logging_reports_no_candidate_evidence(caplog) -> None:
    """无候选设备也应输出能力证据摘要，方便定位为什么没生成实体."""
    payload = {
        "device_id": "power-only-log",
        "category": "light",
        "type": "light",
        "params": {
            "p": True,
            "access_token": "secret",
            "ip": "192.0.2.10",
        },
    }
    coordinator = _Coordinator(data={"power-only": payload})

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.entity_candidates",
    ):
        candidates = list(iter_entity_candidates(coordinator))

    assert candidates == []
    assert "reason=no_projected_candidates" in caplog.text
    assert "prop_count=1" in caplog.text
    assert "prop_ids=('p',)" in caplog.text
    assert "secret" not in caplog.text
    assert "192.0.2.10" not in caplog.text
