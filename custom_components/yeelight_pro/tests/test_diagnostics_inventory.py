"""Diagnostic inventory helper tests for Yeelight Pro."""

from __future__ import annotations

from custom_components.yeelight_pro.diagnostic_inventory import (
    spec_runtime_inventory_diagnostics,
)


def test_spec_runtime_inventory_uses_spec_correction_access_rules() -> None:
    """product-model inventory 诊断应复用 spec correction 的 access 口径."""
    summary = spec_runtime_inventory_diagnostics(
        [
            {
                "ha_product_model": {
                    "product": {"model_id": "YL-compat-access"},
                    "components": [
                        {
                            "properties": [
                                {"prop_id": "l", "access": 7},
                                {"prop_id": "o", "access": 5},
                                {"prop_id": "ct", "access": "读, 写"},
                                {"prop_id": "p", "operators": ["set"]},
                                {"prop_id": "command", "access": "write_only"},
                            ],
                        }
                    ],
                }
            }
        ]
    )

    assert summary["properties_seen"] == 5
    assert summary["readable_properties"] == 4
    assert summary["writable_properties"] == 4
