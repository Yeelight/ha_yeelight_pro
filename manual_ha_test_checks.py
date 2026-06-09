#!/usr/bin/env python3
"""Compatibility facade for root-level manual Home Assistant checks."""
from __future__ import annotations

from manual_ha_test_config_checks import (
    check_config_files,
    check_hacs_json,
    check_manifest,
    check_strings_json,
)
from manual_ha_test_core_checks import (
    check_canonical_models,
    check_client_creation,
    check_config_flow,
    check_ha_core_import,
    check_integration_import,
    check_platform_entities,
    check_services,
    check_utils,
)
from manual_ha_test_projector_checks import check_projectors

__all__ = [
    "check_canonical_models",
    "check_client_creation",
    "check_config_files",
    "check_config_flow",
    "check_hacs_json",
    "check_ha_core_import",
    "check_integration_import",
    "check_manifest",
    "check_platform_entities",
    "check_projectors",
    "check_services",
    "check_strings_json",
    "check_utils",
]
