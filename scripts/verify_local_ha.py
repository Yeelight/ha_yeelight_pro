#!/usr/bin/env python3
"""Verify a local Home Assistant install of Yeelight Pro."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.local_ha_verification.cli import (  # noqa: E402
    build_parser,
    main,
    parse_domain_counts,
)
from scripts.local_ha_verification.constants import (  # noqa: E402
    BAD_LOG_MARKERS,
    DEFAULT_CONTAINER,
    DEFAULT_ENTITY_COUNTS,
    DEFAULT_EXPECTED_CONFIG_ENTRIES,
    DEFAULT_EXPECTED_DEVICES,
    DEFAULT_EXPECTED_ENTITIES,
    DEFAULT_HA_URL,
    DOMAIN,
    FORBIDDEN_INSTALL_NAMES,
    FORBIDDEN_INSTALL_PARTS,
    REQUIRED_RUNTIME_MODULES,
    REQUIRED_SERVICES,
    ROOT,
    SENSITIVE_CACHE_MARKERS,
    SENSITIVE_CACHE_VALUE_PATTERNS,
    SOURCE_COMPONENT_ROOT,
    YEELIGHT_LOG_MARKERS,
)
from scripts.local_ha_verification.diagnostics import (  # noqa: E402
    verify_diagnostics_capabilities,
)
from scripts.local_ha_verification.flow_contracts import (  # noqa: E402
    REQUIRED_OPTIONS_FLOW_TOKENS,
    verify_flow_contracts,
)
from scripts.local_ha_verification.i18n import (  # noqa: E402
    REQUIRED_I18N_LEAF_PATHS,
    TRANSLATION_FILES,
    verify_i18n_contracts,
)
from scripts.local_ha_verification.install import (  # noqa: E402
    RuntimeDiff,
    cache_artifact_count,
    forbidden_install_paths,
    runtime_diff,
    verify_installation,
    verify_required_modules,
)
from scripts.local_ha_verification.options import (  # noqa: E402
    OPTIONAL_CONFIG_ENTRY_OPTION_KEYS,
    REQUIRED_CONFIG_ENTRY_OPTION_KEYS,
    verify_config_entry_options,
)
from scripts.local_ha_verification.platforms import (  # noqa: E402
    installed_enabled_platforms,
    verify_platform_options_alignment,
)
from scripts.local_ha_verification.report import VerificationReport  # noqa: E402
from scripts.local_ha_verification.runtime import (  # noqa: E402
    verify_docker,
    verify_ha_url,
    verify_logs,
    verify_runtime_entities,
    verify_synthetic_log_recovery,
)
from scripts.local_ha_verification.runtime_entities import (  # noqa: E402
    latest_reconciled_active_count,
    latest_reconciled_active_total,
    latest_setup_runtime_lines,
    runtime_entity_counts,
    verify_runtime_entity_counts,
)
from scripts.local_ha_verification.services import (  # noqa: E402
    registered_service_names,
    verify_services,
)
from scripts.local_ha_verification.service_schema import (  # noqa: E402
    SERVICE_FIELD_CONTRACTS,
    documented_service_field_contracts,
    registered_service_schema_fields,
    verify_service_schema_contracts,
)
from scripts.local_ha_verification.storage import (  # noqa: E402
    expected_runtime_entity_counts,
    verify_product_schema_cache,
    verify_storage,
)

__all__ = [
    "BAD_LOG_MARKERS",
    "DEFAULT_CONTAINER",
    "DEFAULT_ENTITY_COUNTS",
    "DEFAULT_EXPECTED_CONFIG_ENTRIES",
    "DEFAULT_EXPECTED_DEVICES",
    "DEFAULT_EXPECTED_ENTITIES",
    "DEFAULT_HA_URL",
    "DOMAIN",
    "FORBIDDEN_INSTALL_NAMES",
    "FORBIDDEN_INSTALL_PARTS",
    "REQUIRED_RUNTIME_MODULES",
    "REQUIRED_SERVICES",
    "REQUIRED_I18N_LEAF_PATHS",
    "ROOT",
    "RuntimeDiff",
    "OPTIONAL_CONFIG_ENTRY_OPTION_KEYS",
    "REQUIRED_CONFIG_ENTRY_OPTION_KEYS",
    "REQUIRED_OPTIONS_FLOW_TOKENS",
    "SENSITIVE_CACHE_MARKERS",
    "SENSITIVE_CACHE_VALUE_PATTERNS",
    "SERVICE_FIELD_CONTRACTS",
    "SOURCE_COMPONENT_ROOT",
    "TRANSLATION_FILES",
    "VerificationReport",
    "YEELIGHT_LOG_MARKERS",
    "build_parser",
    "cache_artifact_count",
    "forbidden_install_paths",
    "installed_enabled_platforms",
    "main",
    "parse_domain_counts",
    "documented_service_field_contracts",
    "registered_service_names",
    "registered_service_schema_fields",
    "runtime_diff",
    "expected_runtime_entity_counts",
    "verify_required_modules",
    "verify_docker",
    "verify_diagnostics_capabilities",
    "verify_flow_contracts",
    "verify_ha_url",
    "verify_i18n_contracts",
    "verify_installation",
    "verify_config_entry_options",
    "verify_logs",
    "verify_runtime_entities",
    "verify_synthetic_log_recovery",
    "verify_runtime_entity_counts",
    "runtime_entity_counts",
    "latest_reconciled_active_count",
    "latest_reconciled_active_total",
    "latest_setup_runtime_lines",
    "verify_platform_options_alignment",
    "verify_product_schema_cache",
    "verify_service_schema_contracts",
    "verify_services",
    "verify_storage",
]


if __name__ == "__main__":
    raise SystemExit(main())
