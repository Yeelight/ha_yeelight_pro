"""Runtime fallback templates must stay within Yeelight documented semantics."""

from __future__ import annotations

from pathlib import Path

from custom_components.yeelight_pro.capabilities import iot_registry
from custom_components.yeelight_pro.converter.runtime_templates import (
    RUNTIME_PROPERTY_TEMPLATES,
)

IOT_DOCS = Path(__file__).resolve().parents[3] / "docs" / "iot"
LAN_ONLY_RUNTIME_PROPS = frozenset({"h", "level"})


def test_runtime_templates_only_use_documented_or_lan_protocol_props() -> None:
    """运行时 fallback 只能引用易来 OpenAPI CSV 或局域网协议已有属性."""
    registry = iot_registry()
    missing = sorted(
        {
            prop_id
            for props in RUNTIME_PROPERTY_TEMPLATES.values()
            for prop_id in props
            if registry.property_spec(prop_id) is None
        }
    )
    lan_doc = (IOT_DOCS / "Yeelight Pro局域网协议.md").read_text(encoding="utf-8")

    assert set(missing).issubset(LAN_ONLY_RUNTIME_PROPS)
    assert "|h|湿度值" in lan_doc
    assert "|level|- 光感档位定义" in lan_doc


def test_runtime_template_access_never_exceeds_iot_registry() -> None:
    """fallback 模板不能把官方只读属性扩大成可写控制."""
    registry = iot_registry()
    violations: list[tuple[str, str, str, str]] = []

    for template_name, props in RUNTIME_PROPERTY_TEMPLATES.items():
        for prop_id, metadata in props.items():
            spec = registry.property_spec(prop_id)
            if spec is None:
                continue
            access = str(metadata.get("access") or "")
            if _template_writable(access) and not spec.writable:
                violations.append((template_name, prop_id, access, spec.access))
            if _template_readable(access) and not spec.readable:
                violations.append((template_name, prop_id, access, spec.access))

    assert violations == []


def _template_writable(access: str) -> bool:
    return "write" in access.lower() or "写" in access


def _template_readable(access: str) -> bool:
    return "read" in access.lower() or "读" in access
