"""Source fixtures for local HA i18n verifier tests."""

from __future__ import annotations

from pathlib import Path


def write_option_schema_sources(
    install_root: Path,
    *,
    extra_option_key: str | None,
) -> None:
    """Write focused option-schema source fixtures."""
    const_lines = [
        'CONF_SCAN_INTERVAL = "scan_interval"',
        'CONF_DEBUG_MODE = "debug_mode"',
    ]
    options_lines = [
        "def options_schema(options):",
        "    return vol.Schema({",
        "        vol.Required(CONF_SCAN_INTERVAL): int,",
        "        vol.Required(CONF_DEBUG_MODE): bool,",
    ]
    if extra_option_key is not None:
        const_lines.append(f'CONF_FUTURE_OPTION = "{extra_option_key}"')
        options_lines.append("        vol.Required(CONF_FUTURE_OPTION): bool,")
    options_lines.extend(["    })"])
    (install_root / "const.py").write_text("\n".join(const_lines), encoding="utf-8")
    (install_root / "config_flow_options.py").write_text(
        "\n".join(options_lines),
        encoding="utf-8",
    )
    (install_root / "config_flow_helpers.py").write_text(
        "\n".join(_config_flow_helper_source_lines()),
        encoding="utf-8",
    )
    (install_root / "device_filter_options.py").write_text(
        "\n".join(_device_filter_option_source_lines()),
        encoding="utf-8",
    )


def write_repair_issue_source(
    install_root: Path,
    *,
    extra_placeholder: str | None,
) -> None:
    """Write a focused repair issue source fixture."""
    placeholder_lines = [
        '                "devices": counts["devices"],',
        '                "gateways": counts["gateways"],',
        '                "areas": counts["areas"],',
        '                "rooms": counts["rooms"],',
        '                "groups": counts["groups"],',
        '                "scenes": counts["scenes"],',
        '                "automations": counts["automations"],',
        '                "added": diff_summary["total_added"],',
        '                "removed": diff_summary["total_removed"],',
        '                "metadata_changed": diff_summary["total_metadata_changed"],',
    ]
    if extra_placeholder is not None:
        placeholder_lines.append(f'                "{extra_placeholder}": "1",')
    (install_root / "repair_issues.py").write_text(
        "\n".join(
            [
                "def create_issue(ir, hass, counts, diff_summary):",
                "    ir.async_create_issue(",
                "        hass,",
                '        "yeelight_pro",',
                '        "device_topology_changed_entry_1",',
                '        translation_key="device_topology_changed",',
                "        translation_placeholders={",
                "            key: str(value)",
                "            for key, value in {",
                *placeholder_lines,
                "            }.items()",
                "        },",
                "    )",
            ]
        ),
        encoding="utf-8",
    )


def _config_flow_helper_source_lines() -> list[str]:
    """Return focused config-flow helper source lines for selector parsing."""
    return [
        'CONNECTION_MODE_CLOUD = "cloud"',
        'CONNECTION_MODE_PRIVATE = "private"',
        'CLOUD_AUTH_METHOD_ACCESS_TOKEN = "access_token"',
        'CLOUD_AUTH_METHOD_SCAN_LOGIN = "scan_login"',
        'CLOUD_REGION_CN = "cn"',
        'CLOUD_REGION_SG = "sg"',
        'CLOUD_REGION_US = "us"',
        'CLOUD_REGION_EU = "de"',
        "CLOUD_REGIONS = [CLOUD_REGION_CN, CLOUD_REGION_SG, CLOUD_REGION_US, CLOUD_REGION_EU]",
        "def user_schema():",
        "    return {",
        "        vol.Required(",
        '            "connection_mode",',
        "        ): selector.SelectSelector(",
        "            selector.SelectSelectorConfig(",
        "                options=[CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE],",
        '                translation_key="connection_mode",',
        "            )",
        "        )",
        "    }",
        "def cloud_auth_method_schema():",
        "    return {",
        "        vol.Required(",
        '            "cloud_auth_method",',
        "        ): selector.SelectSelector(",
        "            selector.SelectSelectorConfig(",
        "                options=[",
        "                    CLOUD_AUTH_METHOD_SCAN_LOGIN,",
        "                    CLOUD_AUTH_METHOD_ACCESS_TOKEN,",
        "                ],",
        '                translation_key="cloud_auth_method",',
        "            )",
        "        )",
        "    }",
        "def cloud_auth_schema():",
        "    return vol.Schema({",
        '        vol.Required("access_token"): str,',
        '        vol.Optional("house_id"): str,',
        "    })",
        "def cloud_region_schema():",
        "    return {",
        '        vol.Required("cloud_region"): selector.SelectSelector(',
        "            selector.SelectSelectorConfig(",
        "                options=CLOUD_REGIONS,",
        '                translation_key="cloud_region",',
        "            )",
        "        )",
        "    }",
    ]


def _device_filter_option_source_lines() -> list[str]:
    """Return focused device-filter option source lines for selector parsing."""
    return [
        'FILTER_MODE_ANY = "or"',
        'FILTER_MODE_ALL = "and"',
        "def device_filter_schema_fields(options):",
        "    return {",
        "        vol.Required(",
        '            "device_import_filter_mode",',
        '        ): selector.SelectSelector(',
        "            selector.SelectSelectorConfig(",
        "                options=[FILTER_MODE_ANY, FILTER_MODE_ALL],",
        '                translation_key="device_import_filter_mode",',
        "            )",
        "        )",
        "    }",
    ]
