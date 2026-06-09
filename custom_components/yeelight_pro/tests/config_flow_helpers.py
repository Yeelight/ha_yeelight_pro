"""Shared helpers for config-flow tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.yeelight_pro.config_flow import YeelightProConfigFlow
from custom_components.yeelight_pro.const import CONNECTION_MODE_CLOUD


@pytest.fixture
def config_flow() -> YeelightProConfigFlow:
    """创建配置流程实例."""
    return YeelightProConfigFlow()


def prepare_cloud_flow(config_flow: YeelightProConfigFlow) -> None:
    """填充进入家庭选择步骤前所需的云端状态."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "api.yeelight.com"
    config_flow._access_token = "test_token"
    config_flow.hass = MagicMock()
