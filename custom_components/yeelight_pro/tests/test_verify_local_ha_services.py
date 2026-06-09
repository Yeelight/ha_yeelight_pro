"""Local HA service verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import (
    VerificationReport,
    registered_service_schema_fields,
    registered_service_names,
    verify_services,
)


def test_registered_service_names_resolves_constants_and_literals(tmp_path: Path) -> None:
    """运行态服务扫描应解析常量和字面量注册，且不导入 HA runtime."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    (install_root / "area_service.py").write_text(
        "\n".join([
            'DOMAIN = "yeelight_pro"',
            'SERVICE_ASSIGN_AREAS = "assign_areas"',
            "def register(hass, handler):",
            "    async_register_admin_service(",
            "        hass, DOMAIN, SERVICE_ASSIGN_AREAS, handler",
            "    )",
        ]),
        encoding="utf-8",
    )
    (install_root / "debug_service.py").write_text(
        "\n".join([
            "def register(hass, handler):",
            '    hass.services.async_register("yeelight_pro", "debug_emit_event", handler)',
        ]),
        encoding="utf-8",
    )
    (install_root / "other.py").write_text(
        'async_register_admin_service(hass, "other_domain", "ignored", handler)',
        encoding="utf-8",
    )

    assert registered_service_names(install_root) == {
        "assign_areas",
        "debug_emit_event",
    }


def test_verify_services_checks_yaml_and_runtime_alignment(tmp_path: Path) -> None:
    """本地 HA 验证应阻断 services.yaml 与运行态注册漂移."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    _write_services_yaml(install_root, extra_services=())
    _write_runtime_services(install_root, assign_devices_required=True)
    report = VerificationReport()

    verify_services(tmp_path, report)

    assert report.ok
    assert any("service definitions/runtime registrations" in fact for fact in report.facts)


def test_registered_service_schema_fields_resolves_imported_constants(tmp_path: Path) -> None:
    """运行态 schema AST 扫描应解析跨模块字段常量且不导入 HA runtime."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    _write_runtime_services(install_root, assign_devices_required=True)

    fields = registered_service_schema_fields(install_root)

    assert fields["assign_areas"] == {"devices": True, "area_id": True}
    assert fields["debug_emit_event"]["source_device_id"] is True
    assert fields["debug_emit_event"]["entry_id"] is False
    assert fields["refresh"] == {"entry_id": False, "refresh_product_schemas": False}
    assert fields["cleanup_registry"] == {
        "entry_id": False,
        "confirm": False,
        "audit_id": False,
    }
    assert fields["refresh_analytics"] == {
        "entry_id": False,
        "endpoint": True,
        "date_code": False,
        "start_date": False,
        "end_date": False,
        "area_id": False,
    }


def test_verify_services_fails_for_unregistered_service(tmp_path: Path) -> None:
    """services.yaml 中声明但 Python 未注册的服务应阻断本地 HA 验证."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    _write_services_yaml(install_root, extra_services=())
    (install_root / "area_service.py").write_text(
        'async_register_admin_service(hass, "yeelight_pro", "assign_areas", handler)',
        encoding="utf-8",
    )
    report = VerificationReport()

    verify_services(tmp_path, report)

    assert not report.ok
    assert any("runtime service registrations missing" in failure for failure in report.failures)
    assert any(
        "services.yaml/runtime service alignment missing" in failure
        for failure in report.failures
    )


def test_verify_services_fails_for_extra_yaml_definition(tmp_path: Path) -> None:
    """未在发布合同中的额外 services.yaml 服务应显式失败."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    _write_services_yaml(install_root, extra_services=("set_scene",))
    _write_runtime_services(install_root, assign_devices_required=True)
    report = VerificationReport()

    verify_services(tmp_path, report)

    assert not report.ok
    assert any("services.yaml definitions unexpected" in failure for failure in report.failures)


def test_verify_services_fails_for_yaml_field_contract_drift(tmp_path: Path) -> None:
    """services.yaml 字段 required/selector 漂移应阻断本地 HA 验证."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    _write_services_yaml(
        install_root,
        extra_services=(),
        devices_required=False,
        devices_selector="text",
    )
    _write_runtime_services(install_root, assign_devices_required=True)
    report = VerificationReport()

    verify_services(tmp_path, report)

    assert not report.ok
    assert any(
        "services.yaml field schema required mismatch for assign_areas.devices"
        in failure
        for failure in report.failures
    )
    assert any(
        "services.yaml field schema selector mismatch for assign_areas.devices"
        in failure
        for failure in report.failures
    )


def test_verify_services_fails_for_runtime_schema_contract_drift(tmp_path: Path) -> None:
    """运行态 handler schema 字段 required 漂移应阻断本地 HA 验证."""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    _write_services_yaml(install_root, extra_services=())
    _write_runtime_services(install_root, assign_devices_required=False)
    report = VerificationReport()

    verify_services(tmp_path, report)

    assert not report.ok
    assert any(
        "runtime service schema required mismatch for assign_areas.devices"
        in failure
        for failure in report.failures
    )


def _write_services_yaml(
    install_root: Path,
    *,
    extra_services: tuple[str, ...],
    devices_required: bool = True,
    devices_selector: str = "object",
) -> None:
    """Write installed services.yaml content with the production field contract."""
    services = _service_yaml_lines(devices_required, devices_selector)
    services.extend(f"{service}:" for service in extra_services)
    (install_root / "services.yaml").write_text(
        "\n".join(services),
        encoding="utf-8",
    )


def _write_runtime_services(
    install_root: Path,
    *,
    assign_devices_required: bool,
) -> None:
    """Write runtime service modules with service registrations and schemas."""
    required_or_optional = "Required" if assign_devices_required else "Optional"
    (install_root / "const.py").write_text(
        "\n".join([
            'DOMAIN = "yeelight_pro"',
            'ATTR_SOURCE_DEVICE_ID = "source_device_id"',
            'ATTR_COMPONENT_ID = "component_id"',
            'ATTR_EVENT_TYPE = "event_type"',
            'ATTR_EVENT_ATTRIBUTES = "event_attributes"',
        ]),
        encoding="utf-8",
    )
    (install_root / "services_runtime.py").write_text(
        "\n".join([
            'DOMAIN = "yeelight_pro"',
            'ATTR_DEVICES = "devices"',
            'ATTR_AREA_ID = "area_id"',
            'ATTR_GATEWAY_ID = "gateway_id"',
            'ATTR_ENTRY_ID = "entry_id"',
            'ATTR_REFRESH_PRODUCT_SCHEMAS = "refresh_product_schemas"',
            'ATTR_CONFIRM = "confirm"',
            'ATTR_AUDIT_ID = "audit_id"',
            'ATTR_ENDPOINT = "endpoint"',
            'ATTR_DATE_CODE = "date_code"',
            'ATTR_START_DATE = "start_date"',
            'ATTR_END_DATE = "end_date"',
            'from .const import ATTR_COMPONENT_ID, ATTR_EVENT_ATTRIBUTES',
            'from .const import ATTR_EVENT_TYPE, ATTR_SOURCE_DEVICE_ID',
            "SERVICE_ASSIGN_AREAS_SCHEMA = vol.Schema({",
            f"    vol.{required_or_optional}(ATTR_DEVICES): list,",
            "    vol.Required(ATTR_AREA_ID): str,",
            "})",
            "SERVICE_AUTO_ASSIGN_AREAS_SCHEMA = vol.Schema({",
            "    vol.Optional(ATTR_GATEWAY_ID): str,",
            "})",
            "SERVICE_DEBUG_EMIT_EVENT_SCHEMA = vol.Schema({",
            "    vol.Optional(ATTR_ENTRY_ID): str,",
            "    vol.Required(ATTR_SOURCE_DEVICE_ID): str,",
            "    vol.Required(ATTR_COMPONENT_ID): str,",
            "    vol.Required(ATTR_EVENT_TYPE): str,",
            "    vol.Optional(ATTR_EVENT_ATTRIBUTES): dict,",
            "})",
            "SERVICE_REFRESH_SCHEMA = vol.Schema({",
            "    vol.Optional(ATTR_ENTRY_ID): str,",
            "    vol.Optional(ATTR_REFRESH_PRODUCT_SCHEMAS): bool,",
            "})",
            "SERVICE_CLEANUP_REGISTRY_SCHEMA = vol.Schema({",
            "    vol.Optional(ATTR_ENTRY_ID): str,",
            "    vol.Optional(ATTR_CONFIRM): bool,",
            "    vol.Optional(ATTR_AUDIT_ID): str,",
            "})",
            "SERVICE_REFRESH_ANALYTICS_SCHEMA = vol.Schema({",
            "    vol.Optional(ATTR_ENTRY_ID): str,",
            "    vol.Required(ATTR_ENDPOINT): str,",
            "    vol.Optional(ATTR_DATE_CODE): str,",
            "    vol.Optional(ATTR_START_DATE): str,",
            "    vol.Optional(ATTR_END_DATE): str,",
            '    vol.Optional("area_id"): str,',
            "})",
            "def register(hass, handler):",
            '    async_register_admin_service(hass, DOMAIN, "assign_areas", handler, schema=SERVICE_ASSIGN_AREAS_SCHEMA)',
            '    async_register_admin_service(hass, DOMAIN, "auto_assign_areas", handler, schema=SERVICE_AUTO_ASSIGN_AREAS_SCHEMA)',
            '    async_register_admin_service(hass, DOMAIN, "debug_emit_event", handler, schema=SERVICE_DEBUG_EMIT_EVENT_SCHEMA)',
            '    async_register_admin_service(hass, DOMAIN, "refresh", handler, schema=SERVICE_REFRESH_SCHEMA)',
            '    hass.services.async_register(DOMAIN, "cleanup_registry", handler, schema=SERVICE_CLEANUP_REGISTRY_SCHEMA)',
            '    hass.services.async_register(DOMAIN, "refresh_analytics", handler, schema=SERVICE_REFRESH_ANALYTICS_SCHEMA)',
        ]),
        encoding="utf-8",
    )


def _service_yaml_lines(devices_required: bool, devices_selector: str) -> list[str]:
    """Return a focused services.yaml fixture."""
    required_text = str(devices_required).lower()
    return [
        "assign_areas:",
        "  fields:",
        "    devices:",
        f"      required: {required_text}",
        "      selector:",
        f"        {devices_selector}:",
        "    area_id:",
        "      required: true",
        "      selector:",
        "        area:",
        "auto_assign_areas:",
        "  fields:",
        "    gateway_id:",
        "      required: false",
        "      selector:",
        "        text:",
        "debug_emit_event:",
        "  fields:",
        "    entry_id:",
        "      required: false",
        "      selector:",
        "        text:",
        "    source_device_id:",
        "      required: true",
        "      selector:",
        "        text:",
        "    component_id:",
        "      required: true",
        "      selector:",
        "        text:",
        "    event_type:",
        "      required: true",
        "      selector:",
        "        text:",
        "    event_attributes:",
        "      required: false",
        "      selector:",
        "        object:",
        "refresh:",
        "  fields:",
        "    entry_id:",
        "      required: false",
        "      selector:",
        "        text:",
        "    refresh_product_schemas:",
        "      required: false",
        "      selector:",
        "        boolean:",
        "cleanup_registry:",
        "  fields:",
        "    entry_id:",
        "      required: false",
        "      selector:",
        "        text:",
        "    confirm:",
        "      required: false",
        "      selector:",
        "        boolean:",
        "    audit_id:",
        "      required: false",
        "      selector:",
        "        text:",
        "refresh_analytics:",
        "  fields:",
        "    entry_id:",
        "      required: false",
        "      selector:",
        "        text:",
        "    endpoint:",
        "      required: true",
        "      selector:",
        "        text:",
        "    date_code:",
        "      required: false",
        "      selector:",
        "        text:",
        "    start_date:",
        "      required: false",
        "      selector:",
        "        text:",
        "    end_date:",
        "      required: false",
        "      selector:",
        "        text:",
        "    area_id:",
        "      required: false",
        "      selector:",
        "        text:",
    ]
