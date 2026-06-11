"""配置流程测试."""

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow_helpers import house_choices
from custom_components.yeelight_pro.config_flow_helpers import (
    cloud_auth_method_schema,
    cloud_region_schema,
    user_schema,
)
from custom_components.yeelight_pro.const import (
    CLOUD_AUTH_METHOD_ACCESS_TOKEN,
    CLOUD_AUTH_METHOD_SCAN_LOGIN,
    CLOUD_REGIONS,
    CONF_CLOUD_REGION,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
    CONNECTION_MODE_PRIVATE,
    CONF_CONNECTION_MODE,
    DEFAULT_CLOUD_REGION,
)


def test_house_choices_normalize_cloud_api_variants() -> None:
    """家庭选择项兼容开放平台字段别名，并跳过无 ID 数据."""
    choices = house_choices([
        {"houseId": "house-b", "houseName": ""},
        {"house_id": "house-a", "house_name": "Alpha"},
        {"id": 3, "name": "Beta"},
        {"name": "Missing ID"},
    ])

    assert choices == {
        "house-a": "Alpha",
        3: "Beta",
        "house-b": "易来家庭",
    }


def test_cloud_auth_method_schema_uses_localized_labels() -> None:
    """认证方式选择项应使用 HA selector 翻译合同."""
    schema = cloud_auth_method_schema()
    field = next(iter(schema.schema))
    auth_selector = schema.schema[field]

    assert auth_selector.config["translation_key"] == "cloud_auth_method"
    assert auth_selector.config["options"] == [
        CLOUD_AUTH_METHOD_SCAN_LOGIN,
        CLOUD_AUTH_METHOD_ACCESS_TOKEN,
    ]


def test_cloud_region_schema_uses_localized_region_selector() -> None:
    """云端区域选择项应使用 HA selector 翻译合同."""
    schema = cloud_region_schema()
    field = next(iter(schema.schema))
    region_selector = schema.schema[field]

    assert field.schema == CONF_CLOUD_REGION
    assert field.default() == DEFAULT_CLOUD_REGION
    assert region_selector.config["translation_key"] == "cloud_region"
    assert region_selector.config["options"] == CLOUD_REGIONS


def test_user_schema_uses_localized_connection_mode_selector() -> None:
    """连接模式选择项应使用 HA selector 翻译合同."""
    schema = user_schema()
    field = next(iter(schema.schema))
    mode_selector = schema.schema[field]

    assert mode_selector.config["translation_key"] == "connection_mode"
    assert mode_selector.config["options"] == [
        CONNECTION_MODE_CLOUD,
        CONNECTION_MODE_PRIVATE,
        CONNECTION_MODE_LAN,
    ]


class TestConfigFlow:
    """配置流程测试."""

    def test_init(self, config_flow):
        """测试初始化."""
        assert config_flow.VERSION == 1
        assert config_flow._connection_mode is None
        assert config_flow._cloud_auth_method == CLOUD_AUTH_METHOD_SCAN_LOGIN

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
        assert result["step_id"] == "cloud_region"
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
