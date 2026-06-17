"""Expected release files for HACS preflight contract tests."""

from __future__ import annotations

from .hacs_preflight_expected_components import EXPECTED_COMPONENT_FILES
from .hacs_preflight_expected_scripts import EXPECTED_SCRIPT_FILES
from .hacs_preflight_expected_tests import EXPECTED_TEST_FILES

EXPECTED_RELEASE_FILES = (
    EXPECTED_SCRIPT_FILES
    | {f"custom_components/yeelight_pro/{path}" for path in EXPECTED_COMPONENT_FILES}
    | {f"custom_components/yeelight_pro/tests/{path}" for path in EXPECTED_TEST_FILES}
)
