"""Automation and runtime-option preflight checks for Yeelight Pro."""

from __future__ import annotations

from pathlib import Path


def check_automation_contract_tests(component_root: Path) -> list[str]:
    """Ensure release-sensitive automation entry points have tests."""
    errors: list[str] = []
    device_trigger = component_root / "device_trigger.py"
    device_trigger_test = component_root / "tests" / "test_device_trigger.py"
    device_trigger_runtime_test = (
        component_root / "tests" / "test_device_trigger_runtime.py"
    )
    device_trigger_helpers = component_root / "tests" / "device_trigger_helpers.py"
    if not device_trigger.exists():
        return errors
    if not device_trigger_test.exists():
        errors.append("device_trigger.py requires tests/test_device_trigger.py")
    if not device_trigger_runtime_test.exists():
        errors.append(
            "device_trigger.py requires tests/test_device_trigger_runtime.py"
        )
    if not device_trigger_helpers.exists():
        errors.append("device_trigger.py requires tests/device_trigger_helpers.py")
    if errors:
        return errors

    content = device_trigger_test.read_text(encoding="utf-8")
    errors.extend(_missing_tokens(
        content,
        {
        "async_get_triggers": "lists projected device triggers",
        "async_validate_trigger_config": "rejects unsupported device triggers",
        "async_attach_trigger": "attaches Home Assistant event trigger",
        "InvalidDeviceAutomationConfig": "asserts invalid trigger failures",
        "multi_spin": "keeps scene-panel multi-spin trigger coverage",
        "absolut_spin": "keeps scene-panel absolut-spin trigger coverage",
        },
        "test_device_trigger.py",
    ))
    errors.extend(_missing_tokens(
        device_trigger_runtime_test.read_text(encoding="utf-8"),
        {
            "async_attach_trigger": "attaches Home Assistant event trigger",
            "DEVICE_EVENT_TYPE": "matches Yeelight Pro runtime event bus payload",
            "register_switch_event_device": "matches switch component events",
            "trigger-context": "preserves runtime event context coverage",
        },
        "test_device_trigger_runtime.py",
    ))
    errors.extend(_missing_tokens(
        device_trigger_helpers.read_text(encoding="utf-8"),
        {
            "event_device_payload": "device trigger event payload fixture",
            "register_event_device": "scene panel registration helper",
            "register_switch_event_device": "switch event registration helper",
            "multi spin": "scene-panel multi-spin fixture coverage",
            "absolut spin": "scene-panel absolut-spin fixture coverage",
        },
        "device_trigger_helpers.py",
    ))
    return errors


def check_runtime_options_contract_tests(component_root: Path) -> list[str]:
    """Ensure runtime-only options keep their selective reload contract."""
    errors: list[str] = []
    runtime_options = component_root / "runtime_options.py"
    runtime_options_test = component_root / "tests" / "test_runtime_options.py"
    debug_service = component_root / "debug_service.py"
    debug_service_test = component_root / "tests" / "test_debug_service.py"
    if not runtime_options.exists():
        errors.append("runtime_options.py is required for selective options reload")
        return errors
    if not runtime_options_test.exists():
        errors.append("runtime_options.py requires tests/test_runtime_options.py")
        return errors
    if not debug_service.exists():
        errors.append("runtime options require debug_service.py")
        return errors
    if not debug_service_test.exists():
        errors.append("debug_service.py requires tests/test_debug_service.py")
        return errors

    source = runtime_options.read_text(encoding="utf-8")
    test_source = runtime_options_test.read_text(encoding="utf-8")
    errors.extend(_missing_tokens(
        source,
        {
            "CONF_EXPERIMENTAL_PLATFORMS": "reload on platform set changes",
            "CONF_HIDE_UNKNOWN_ENTITIES": "reload on entity projection changes",
            "apply_options": "runtime-only options apply without reload",
            "async_delete_topology_changed_issues": "clears disabled Repairs issues",
            "async_reload": "falls back to Home Assistant entry reload",
        },
        "runtime_options.py",
    ))
    errors.extend(_missing_tokens(
        test_source,
        {
            "without_reload": "runtime-only options do not reload",
            "entity_projection_changes": "entity-affecting options reload",
            "runtime_missing": "missing runtime falls back to reload",
            "clears_topology_repairs": "disabled topology Repairs are cleared",
        },
        "test_runtime_options.py",
    ))
    errors.extend(_missing_tokens(
        debug_service.read_text(encoding="utf-8"),
        {
            "async_register_admin_service": "debug service remains admin-only",
            "coordinator.debug_mode": "debug service is gated by debug_mode",
            "async_handle_runtime_event": "debug service uses runtime event bridge",
        },
        "debug_service.py",
    ))
    errors.extend(_missing_tokens(
        debug_service_test.read_text(encoding="utf-8"),
        {
            "test_debug_emit_event_service_rejects_disabled_debug_mode": (
                "disabled debug-mode service rejection coverage"
            ),
            "assert_not_awaited": "disabled debug service does not dispatch event",
            "debug mode is disabled": "debug-mode disabled error contract",
        },
        "test_debug_service.py",
    ))
    return errors


def _missing_tokens(
    content: str,
    required_tokens: dict[str, str],
    label: str,
) -> list[str]:
    """Return missing token errors for a preflight source."""
    return [
        f"{label} missing {reason}: {token}"
        for token, reason in required_tokens.items()
        if token not in content
    ]
