"""Static data for Yeelight Pro HACS preflight checks."""

from __future__ import annotations

from scripts import hacs_preflight_diagnostics_data as _diagnostics_data
from scripts import hacs_preflight_entity_filter_data as _entity_filter_data
from scripts.hacs_preflight_release_files import (
    REQUIRED_RELEASE_FILES as REQUIRED_RELEASE_FILES,
)

DIAGNOSTICS_CONTRACT_TEST_TOKENS = (
    _diagnostics_data.DIAGNOSTICS_CONTRACT_TEST_TOKENS
)
DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES = (
    _diagnostics_data.DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES
)
DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES = (
    _diagnostics_data.DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES
)
DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES = (
    _diagnostics_data.DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES
)
DYNAMIC_ENTITY_FILTER_CONTRACT_TOKENS = (
    _entity_filter_data.DYNAMIC_ENTITY_FILTER_CONTRACT_TOKENS
)

REQUIRED_MANIFEST_FIELDS = {
    "domain",
    "name",
    "codeowners",
    "config_flow",
    "documentation",
    "iot_class",
    "version",
}
REQUIRED_HACS_FIELDS = {
    "name",
    "homeassistant",
    "render_readme",
    "zip_release",
    "filename",
}
HACS_PUBLISH_REQUIRED_CHECKS = {
    "compile": (
        "python3",
        "-m",
        "compileall",
        "-q",
        "custom_components/yeelight_pro",
        "scripts",
        "hacs_publish.py",
    ),
    "lint": (
        "ruff",
        "check",
        "custom_components/yeelight_pro",
        "scripts",
        "hacs_publish.py",
    ),
    "type-check": (
        "mypy",
        "--ignore-missing-imports",
        "--explicit-package-bases",
        "custom_components/yeelight_pro",
        "scripts",
        "hacs_publish.py",
    ),
    "tests": ("pytest", "-q"),
    "local preflight": ("python3", "validate_hacs.py"),
    "release zip": ("python3", "scripts/check_release_zip.py"),
}
RELEASE_QUALITY_GATE_TOKENS = {
    "requirements_test.txt": {
        "ruff": "ruff dependency for local and CI release checks",
        "mypy": "mypy dependency for local and CI release checks",
    },
    "hacs_publish.py": {
        "CHECKS": "local release command list",
        "compileall": "local release compile gate",
        "ruff": "local release lint gate",
        "mypy": "local release mypy gate",
        '"--ignore-missing-imports"': "local release mypy option",
        '"--explicit-package-bases"': "local release mypy package boundary",
        '"hacs_publish.py"': "local release script self-check",
    },
    ".github/workflows/validate.yaml": {
        "python -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py": (
            "GitHub validate compile command"
        ),
        "Lint integration": "GitHub validate lint step",
        "ruff check custom_components/yeelight_pro scripts hacs_publish.py": (
            "GitHub validate lint command"
        ),
        "Type-check integration": "GitHub validate type-check step",
        "mypy --ignore-missing-imports --explicit-package-bases custom_components/yeelight_pro scripts hacs_publish.py": (
            "GitHub validate type-check command"
        ),
    },
    ".github/workflows/release.yaml": {
        "Install test dependencies": "GitHub release dependency install step",
        "Run full release gate": "GitHub release full local gate step",
        "python hacs_publish.py --check": "GitHub release full local gate command",
        "python scripts/check_release_zip.py --write yeelight_pro.zip": (
            "GitHub release zip creation command"
        ),
    },
    "README.md": {
        "python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py": (
            "English README compile command"
        ),
        "ruff check custom_components/yeelight_pro scripts hacs_publish.py": (
            "English README lint command"
        ),
        "mypy --ignore-missing-imports --explicit-package-bases custom_components/yeelight_pro scripts hacs_publish.py": (
            "English README type-check command"
        ),
        "python3 scripts/sync_local_ha_runtime.py": (
            "English README local HA runtime sync command"
        ),
    },
    "README_zh.md": {
        "python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py": (
            "Chinese README compile command"
        ),
        "ruff check custom_components/yeelight_pro scripts hacs_publish.py": (
            "Chinese README lint command"
        ),
        "mypy --ignore-missing-imports --explicit-package-bases custom_components/yeelight_pro scripts hacs_publish.py": (
            "Chinese README type-check command"
        ),
        "python3 scripts/sync_local_ha_runtime.py": (
            "Chinese README local HA runtime sync command"
        ),
    },
    "RELEASE_GUIDE.md": {
        "python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py": (
            "release guide compile command"
        ),
        "ruff check custom_components/yeelight_pro scripts hacs_publish.py": (
            "release guide lint command"
        ),
        "mypy --ignore-missing-imports --explicit-package-bases custom_components/yeelight_pro scripts hacs_publish.py": (
            "release guide type-check command"
        ),
        "compile, lint, type-check, tests, local preflight": (
            "release guide workflow coverage text"
        ),
        "release.yaml`: runs the full local release gate": (
            "release guide release workflow coverage text"
        ),
    },
}
JSON_FILES = {
    "hacs.json",
    "custom_components/yeelight_pro/manifest.json",
    "custom_components/yeelight_pro/strings.json",
    "custom_components/yeelight_pro/translations/en.json",
    "custom_components/yeelight_pro/translations/zh-Hans.json",
}
