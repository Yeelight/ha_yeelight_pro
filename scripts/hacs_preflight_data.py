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
        "--exclude",
        "custom_components/yeelight_pro/tests",
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
        '"--exclude"': "local release mypy test-suite exclusion",
        '"custom_components/yeelight_pro/tests"': (
            "local release mypy excludes HA test doubles"
        ),
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
        "mypy --ignore-missing-imports --explicit-package-bases --exclude 'custom_components/yeelight_pro/tests' custom_components/yeelight_pro scripts hacs_publish.py": (
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
    ".github/ISSUE_TEMPLATE/bug_report.yml": {
        "Integration version": "bug report version field",
        "Redacted diagnostics": "bug report redacted diagnostics field",
        "Privacy confirmation": "bug report privacy confirmation",
        "access tokens, refresh tokens, house IDs, device IDs, MAC addresses": (
            "bug report privacy boundary"
        ),
    },
    ".github/ISSUE_TEMPLATE/feature_request.yml": {
        "Protocol evidence": "feature request protocol evidence field",
        "Sanitized product samples": "feature request sanitized sample field",
        "needs-product-decision": "feature request product-decision label",
        "uncertain capabilities may stay hidden": (
            "feature request uncertainty boundary"
        ),
    },
    ".github/ISSUE_TEMPLATE/support.yml": {
        "Support request": "support template title",
        "Redacted diagnostics or verifier output": "support redacted verifier field",
        "WebSocket live updates": "support live-update topic",
        "raw payloads": "support raw payload privacy boundary",
    },
    "README.md": {
        "python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py": (
            "English README compile command"
        ),
        "ruff check custom_components/yeelight_pro scripts hacs_publish.py": (
            "English README lint command"
        ),
        "mypy --ignore-missing-imports --explicit-package-bases --exclude custom_components/yeelight_pro/tests custom_components/yeelight_pro scripts hacs_publish.py": (
            "English README type-check command"
        ),
        "python3 scripts/sync_local_ha_runtime.py": (
            "English README local HA runtime sync command"
        ),
        "python3 scripts/verify_lan_gateway.py": (
            "English README production LAN gateway probe command"
        ),
        "must remain fail-closed": (
            "English README production probe fail-closed boundary"
        ),
        "Cloud event notifications use the explicit `live_updates` WebSocket runtime": (
            "English README WebSocket-only event-notification boundary"
        ),
        "Polling remains the default full-state refresh path": (
            "English README live event transport boundary"
        ),
    },
    "README_zh.md": {
        "python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py": (
            "Chinese README compile command"
        ),
        "ruff check custom_components/yeelight_pro scripts hacs_publish.py": (
            "Chinese README lint command"
        ),
        "mypy --ignore-missing-imports --explicit-package-bases --exclude custom_components/yeelight_pro/tests custom_components/yeelight_pro scripts hacs_publish.py": (
            "Chinese README type-check command"
        ),
        "python3 scripts/sync_local_ha_runtime.py": (
            "Chinese README local HA runtime sync command"
        ),
        "python3 scripts/verify_lan_gateway.py": (
            "Chinese README production LAN gateway probe command"
        ),
        "必须保持 fail-closed": (
            "Chinese README production probe fail-closed boundary"
        ),
        "云端事件通知使用显式 `live_updates` WebSocket runtime": (
            "Chinese README WebSocket-only event-notification boundary"
        ),
        "轮询仍作为默认全量状态刷新路径": (
            "Chinese README live event transport boundary"
        ),
    },
    "RELEASE_GUIDE.md": {
        "python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py": (
            "release guide compile command"
        ),
        "ruff check custom_components/yeelight_pro scripts hacs_publish.py": (
            "release guide lint command"
        ),
        "mypy --ignore-missing-imports --explicit-package-bases --exclude custom_components/yeelight_pro/tests custom_components/yeelight_pro scripts hacs_publish.py": (
            "release guide type-check command"
        ),
        "compile, lint, type-check, tests, local preflight": (
            "release guide workflow coverage text"
        ),
        "release.yaml`: runs the full local release gate": (
            "release guide release workflow coverage text"
        ),
        "Use semantic versioning": "release guide semantic versioning policy",
        "GitHub release tag, `manifest.json` version, and `CHANGELOG.md`": (
            "release guide version alignment policy"
        ),
        "Triage public issues only through the checked-in GitHub issue templates": (
            "release guide support workflow policy"
        ),
        "raw payloads before continuing technical analysis": (
            "release guide support privacy boundary"
        ),
        "Yeelight documentation or sanitized sample evidence": (
            "release guide feature evidence policy"
        ),
        "python3 scripts/verify_lan_gateway.py": (
            "release guide production LAN gateway probe command"
        ),
        "Guarded production probes must stay fail-closed": (
            "release guide production probe fail-closed policy"
        ),
    },
    "docs/TEST_REPORT.md": {
        "python3 scripts/verify_lan_gateway.py": (
            "test report production LAN gateway probe command"
        ),
        "默认都必须 fail-closed": (
            "test report production probe fail-closed boundary"
        ),
        "受控生产探针默认都必须 fail-closed": (
            "test report guarded production probe boundary"
        ),
    },
    "docs/RELEASE_STATUS.md": {
        ".github/ISSUE_TEMPLATE/bug_report.yml": (
            "release status bug template material"
        ),
        ".github/ISSUE_TEMPLATE/feature_request.yml": (
            "release status feature template material"
        ),
        ".github/ISSUE_TEMPLATE/support.yml": (
            "release status support template material"
        ),
        "脱敏 diagnostics/logs": "release status support privacy policy",
        "Yeelight 文档或脱敏样本证据": "release status feature evidence policy",
        "CHANGELOG 和 manifest version": "release status version review policy",
    },
    "docs/GOAL_COMPLETION_AUDIT.md": {
        "cli&{device}&{qrcodeId}": "goal audit scan-login QR payload boundary",
        "CN/SG/US/DE": "goal audit regional account domains",
        "一个账号/家庭一个 config entry": "goal audit multi-account entry model",
        "WebSocket 事件通知": (
            "goal audit WebSocket event-notification status"
        ),
        "live_runtime.py -> YeelightPushWebSocketTransport -> push_transport.py ws_connect -> subscribe/heartbeat -> prop/event -> coordinator_runtime.py async_handle_push_payload": (
            "goal audit WebSocket runtime chain"
        ),
        "hostless one-shot UDP fallback": "goal audit LAN discovery boundary",
        "真实设备 picker A": "goal audit picker decision label",
        "setup 和 options 均支持真实设备 picker": "goal audit picker setup/options boundary",
        "cleanup B": "goal audit cleanup decision label",
        "dry-run + audit_id confirm，只禁用 stale entities": (
            "goal audit cleanup non-destructive boundary"
        ),
        "missing_confirm_flag": "goal audit production WebSocket fail-closed result",
        "network_attempted=false": "goal audit production WebSocket no-network result",
        "python3 scripts/verify_scan_login.py": (
            "goal audit production scan-login probe command"
        ),
        "--confirm-production-scan-login": (
            "goal audit production scan-login explicit confirm flag"
        ),
        "YEELIGHT_PRO_SCAN_LOGIN_DEVICE": (
            "goal audit production scan-login device env guard"
        ),
        "python3 scripts/verify_cloud_devices.py": (
            "goal audit production cloud devices probe command"
        ),
        "--confirm-production-cloud-devices": (
            "goal audit production cloud devices explicit confirm flag"
        ),
        "YEELIGHT_PRO_CLOUD_ACCESS_TOKEN": (
            "goal audit production cloud devices token env guard"
        ),
        "YEELIGHT_PRO_CLOUD_HOUSE_ID": (
            "goal audit production cloud devices house env guard"
        ),
        "python3 scripts/verify_lan_gateway.py": (
            "goal audit production LAN gateway probe command"
        ),
        "--confirm-production-lan-gateway": (
            "goal audit production LAN gateway explicit confirm flag"
        ),
        "YEELIGHT_PRO_LAN_GATEWAY_HOST": (
            "goal audit production LAN gateway host env guard"
        ),
        "输出仅包含脱敏聚合结果": (
            "goal audit production probe redacted aggregate boundary"
        ),
    },
    "docs/IOT_SPEC_REGISTRY.md": {
        "The open platform event-notification material documents WebSocket": (
            "IoT registry WebSocket source-material boundary"
        ),
        "Cloud event notifications use the WebSocket runtime": (
            "IoT registry WebSocket runtime boundary"
        ),
        "Received `prop` and `event` payloads are dispatched to the coordinator": (
            "IoT registry WebSocket data-frame boundary"
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
