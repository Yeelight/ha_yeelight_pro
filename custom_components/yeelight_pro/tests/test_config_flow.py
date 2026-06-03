"""配置流程测试."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow import YeelightProConfigFlow
from custom_components.yeelight_pro.const import (
    DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    CONF_CONNECTION_MODE,
    CONF_ACCESS_TOKEN,
    CONF_HOUSE_ID,
)


@pytest.fixture
def config_flow():
    """创建配置流程实例."""
    return YeelightProConfigFlow()


class TestConfigFlow:
    """配置流程测试."""

    def test_init(self, config_flow):
        """测试初始化."""
        assert config_flow.VERSION == 1
        assert config_flow._connection_mode is None

    @pytest.mark.asyncio
    async def test_user_step_shows_form(self, config_flow):
        """测试用户步骤显示表单."""
        result = await config_flow.async_step_user()
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_user_step_cloud_mode(self, config_flow):
        """测试选择云端模式."""
        result = await config_flow.async_step_user(
            {CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "cloud_auth"
        assert config_flow._connection_mode == CONNECTION_MODE_CLOUD

    @pytest.mark.asyncio
    async def test_user_step_private_mode(self, config_flow):
        """测试选择私有模式."""
        result = await config_flow.async_step_user(
            {CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "private_config"
        assert config_flow._connection_mode == CONNECTION_MODE_PRIVATE

    @pytest.mark.asyncio
    @patch("custom_components.yeelight_pro.config_flow.async_get_clientsession")
    @patch("custom_components.yeelight_pro.config_flow.YeelightProClient")
    async def test_cloud_auth_success(self, mock_client_class, mock_get_session, config_flow):
        """测试云端认证成功."""
        mock_client = AsyncMock()
        mock_client.validate_auth.return_value = True
        mock_client_class.return_value = mock_client

        # 模拟 session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        config_flow._connection_mode = CONNECTION_MODE_CLOUD
        config_flow._domain = "api.yeelight.com"
        config_flow.hass = MagicMock()

        result = await config_flow.async_step_cloud_auth(
            {CONF_ACCESS_TOKEN: "test_token"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "cloud_houses"
        assert config_flow._access_token == "test_token"

    @pytest.mark.asyncio
    @patch("custom_components.yeelight_pro.config_flow.async_get_clientsession")
    @patch("custom_components.yeelight_pro.config_flow.YeelightProClient")
    async def test_cloud_auth_invalid_token(self, mock_client_class, mock_get_session, config_flow):
        """测试云端认证失败."""
        from custom_components.yeelight_pro.core.exceptions import AuthenticationError

        mock_client = AsyncMock()
        mock_client.validate_auth.side_effect = AuthenticationError("Invalid")
        mock_client_class.return_value = mock_client

        # 模拟 session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        config_flow._connection_mode = CONNECTION_MODE_CLOUD
        config_flow._domain = "api.yeelight.com"
        config_flow.hass = MagicMock()

        result = await config_flow.async_step_cloud_auth(
            {CONF_ACCESS_TOKEN: "invalid_token"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_auth"
