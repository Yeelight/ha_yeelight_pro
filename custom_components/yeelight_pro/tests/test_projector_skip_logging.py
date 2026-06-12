"""Projector DEBUG skip logging regressions."""

from __future__ import annotations

import logging

from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.climate import project_climates
from custom_components.yeelight_pro.projector.cover import project_covers
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.converter.product import (
    RuntimeInferredProductModelBuilder,
)

from .projection_helpers import DOMAIN, projection_payload


def test_sensor_projection_logs_missing_property_evidence(caplog) -> None:
    """传感器品类缺少文档属性时应输出稳定 reason."""
    device = projection_payload(
        device_id="sensor-empty-log",
        category="light_sensor",
        component_id="ambient_light_sensor",
        state={},
        component_category="ambient light sensor",
    )
    device["name"] = "用户自定义照度名称"

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.projector.sensor",
    ):
        assert project_sensors(device, domain=DOMAIN) == []

    assert "reason=missing_sensor_property_evidence" in caplog.text
    assert "device_id=sensor-empty-log" in caplog.text
    assert "用户自定义照度名称" not in caplog.text


def test_binary_sensor_projection_logs_event_style_block(caplog) -> None:
    """事件输入设备里的二态属性被拦截时应有可诊断 reason."""
    device = projection_payload(
        device_id="panel-binary-log",
        category="scene_panel",
        component_id="scene_panel",
        state={"mv": True},
        component_category="scene_panel",
    )
    device["name"] = "用户自定义面板名称"

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.projector.binary_sensor",
    ):
        assert project_binary_sensors(device, domain=DOMAIN) == []

    assert "reason=event_style_component_owns_property" in caplog.text
    assert "prop_id=mv" in caplog.text
    assert "用户自定义面板名称" not in caplog.text


def test_event_projection_logs_unsupported_schema_events(caplog) -> None:
    """schema 事件缺少易来 registry 支撑时应记录拒绝原因."""
    device = projection_payload(
        device_id="event-skip-log",
        category="other",
        component_id="vendor_component",
        state={},
        component_category="vendor component",
        product_events=[{"event_id": 999, "name": "vendor.private"}],
    )
    device["name"] = "用户自定义事件设备"

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.projector.event_helpers",
    ):
        assert project_events(device, domain=DOMAIN) == []

    assert "reason=missing_supported_event_evidence" in caplog.text
    assert "component_id=vendor_component" in caplog.text
    assert "用户自定义事件设备" not in caplog.text


def test_cover_projection_logs_missing_position_evidence(caplog) -> None:
    """窗帘组件缺少位置属性时应记录稳定拒绝原因."""
    device = projection_payload(
        device_id="cover-skip-log",
        category="curtain",
        component_id="vendor_curtain_component",
        state={"p": True},
        params={"p": True},
        component_category="curtain",
    )
    device["name"] = "用户自定义窗帘名称"

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.projector.cover",
    ):
        assert project_covers(device, domain=DOMAIN) == []

    assert "reason=missing_cover_position_properties" in caplog.text
    assert "component_id=vendor_curtain_component" in caplog.text
    assert "用户自定义窗帘名称" not in caplog.text


def test_climate_projection_logs_missing_property_evidence(caplog) -> None:
    """温控组件缺少温控属性时应记录稳定拒绝原因."""
    device = projection_payload(
        device_id="climate-skip-log",
        category="temp_control",
        component_id="vendor_climate_component",
        state={"mv": True},
        params={"mv": True},
        component_category="air_conditioner",
    )
    device["name"] = "用户自定义温控名称"

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.projector.climate",
    ):
        assert project_climates(device, domain=DOMAIN) == []

    assert "reason=missing_climate_properties" in caplog.text
    assert "component_id=vendor_climate_component" in caplog.text
    assert "用户自定义温控名称" not in caplog.text


def test_event_projection_logs_missing_product_model(caplog) -> None:
    """缺少 product schema 的事件型设备应记录无法投影原因."""
    device = {
        "device_id": "event-no-schema-log",
        "category": "scene_panel",
        "type": "scene_panel",
    }

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.projector.event",
    ):
        assert project_events(device, domain=DOMAIN) == []

    assert "reason=missing_product_model" in caplog.text
    assert "device_id=event-no-schema-log" in caplog.text


def test_runtime_registry_event_inference_logs_without_user_names(caplog) -> None:
    """registry 事件补全应留下调试线索，但不能输出用户自定义名称."""
    payload = {
        "device_id": "contact-runtime-log",
        "name": "用户自定义门磁名称",
        "model_id": "runtime-contact-log",
        "type": "binary_sensor",
        "category": "contact_sensor",
        "params": {"dc": True, "alm": False},
    }

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.converter.runtime_registry_events",
    ):
        RuntimeInferredProductModelBuilder().build(payload)

    assert "Inferred runtime events from IoT registry" in caplog.text
    assert "device_id=contact-runtime-log" in caplog.text
    assert "event_types=['door_open', 'door_close', 'door_alarm', 'door_normal']" in (
        caplog.text
    )
    assert "用户自定义门磁名称" not in caplog.text


def test_runtime_registry_event_inference_logs_missing_identity(caplog) -> None:
    """宽泛人体品类无法唯一映射事件组件时，应记录明确跳过原因."""
    payload = {
        "device_id": "human-runtime-log",
        "name": "用户自定义人体名称",
        "model_id": "runtime-human-log",
        "type": "binary_sensor",
        "category": "human_sensor",
        "params": {"mv": True},
    }

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.yeelight_pro.converter.runtime_registry_events",
    ):
        RuntimeInferredProductModelBuilder().build(payload)

    assert "Skipping runtime registry event inference" in caplog.text
    assert "reason=missing_registry_component_identity" in caplog.text
    assert "device_id=human-runtime-log" in caplog.text
    assert "用户自定义人体名称" not in caplog.text
