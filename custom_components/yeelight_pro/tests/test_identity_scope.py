"""Identity scope stability tests."""
from __future__ import annotations

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_PRIVATE,
)
from custom_components.yeelight_pro.identity import (
    entry_identity_alias_scopes,
    entry_identity_scope,
)


def test_private_identity_scope_uses_iot_base_url_for_legacy_stability() -> None:
    """私有部署从旧 IoT 前缀迁移到 root URL 后，实体 scope 必须保持稳定."""
    root_entry = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://api-test.yeedev.com",
        CONF_HOUSE_ID: 99529,
    }
    legacy_entry = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://api-test.yeedev.com/apis/iot",
        CONF_HOUSE_ID: 99529,
    }

    assert entry_identity_scope(root_entry) == entry_identity_scope(legacy_entry)


def test_private_identity_alias_scopes_include_root_endpoint_scope() -> None:
    """私有部署根 URL 输入应能识别早期 root 指纹遗留实体为 alias."""
    entry = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://api-test.yeedev.com",
        CONF_HOUSE_ID: 99529,
    }

    aliases = entry_identity_alias_scopes(entry)

    assert "private_endpoint_1ba60251fd570476_house_99529" in aliases
    assert entry_identity_scope(entry) not in aliases
