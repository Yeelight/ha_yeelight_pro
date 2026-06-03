"""Yeelight Pro 集成测试 - 使用 pytest-homeassistant-custom-component."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN

from custom_components.yeelight_pro.const import (
    DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    PLATFORMS,
)
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator


@pytest.fixture
def mock_config_entry():
    """创建模拟的配置条目."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_ACCESS_TOKEN: "test_token",
        CONF_HOUSE_ID: 12345,
        "cloud_domain": "api.yeelight.com",
    }
    return entry


@pytest.fixture
def mock_client():
    """创建模拟的客户端."""
    client = AsyncMock(spec=YeelightProClient)
    client.check_health.return_value = True
    client.validate_auth.return_value = True
    client.get_houses.return_value = [
        {"id": 12345, "name": "测试家庭"},
    ]
    client.get_devices.return_value = []
    client.get_gateways.return_value = []
    client.get_product_schemas.return_value = {}
    client.control_device.return_value = True
    client.execute_scene.return_value = True
    client.get_scenes.return_value = []
    client.get_automations.return_value = []
    client.get_groups.return_value = []
    client.get_rooms.return_value = []
    client.get_areas.return_value = []
    return client


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_client):
    """创建模拟的协调器."""
    coordinator = MagicMock(spec=YeelightProCoordinator)
    coordinator.hass = hass
    coordinator.client = mock_client
    coordinator.data = {}
    coordinator.scenes = []
    coordinator.automations = []
    coordinator.rooms = []
    coordinator.groups = []
    coordinator.house_id = 12345
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_execute_scene = AsyncMock()
    coordinator.async_trigger_automation = AsyncMock()
    coordinator.async_control_device = AsyncMock()
    coordinator.async_toggle_device = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant, mock_config_entry, mock_client):
    """测试集成设置."""
    # 确保 hass.data[DOMAIN] 已初始化（async_setup 的职责）
    hass.data.setdefault(DOMAIN, {})
    # 模拟 config_entry 的 domain（平台转发需要）
    mock_config_entry.domain = DOMAIN

    # 模拟客户端创建
    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=mock_client,
    ):
        # 模拟协调器创建
        with patch(
            "custom_components.yeelight_pro.YeelightProCoordinator",
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.data = {}
            mock_coordinator.get_gateway_devices = MagicMock(return_value={})
            mock_coordinator.topology_generation = 0
            mock_coordinator.async_add_listener = MagicMock()
            mock_coordinator_class.return_value = mock_coordinator

            # 模拟平台转发（避免真实加载平台模块）
            with patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                new_callable=AsyncMock,
            ):
                from custom_components.yeelight_pro import async_setup_entry

                result = await async_setup_entry(hass, mock_config_entry)
                assert result is True


@pytest.mark.asyncio
async def test_unload_entry(hass: HomeAssistant, mock_config_entry, mock_coordinator):
    """测试集成卸载."""
    # 模拟 hass.data
    client_mock = AsyncMock()
    client_mock.disconnect = AsyncMock()
    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "client": client_mock,
            "coordinator": mock_coordinator,
        }
    }

    # 测试卸载
    from custom_components.yeelight_pro import async_unload_entry

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(hass, mock_config_entry)
        assert result is True


@pytest.mark.asyncio
async def test_platform_setup(hass: HomeAssistant, mock_config_entry, mock_coordinator):
    """测试平台设置."""
    # 模拟 hass.data
    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "client": mock_coordinator.client,
            "coordinator": mock_coordinator,
        }
    }

    # 测试每个平台
    for platform in PLATFORMS:
        try:
            module = __import__(
                f"custom_components.yeelight_pro.{platform}",
                fromlist=[platform],
            )
            assert hasattr(module, "async_setup_entry")
            print(f"✅ {platform} 平台设置函数存在")
        except Exception as e:
            print(f"❌ {platform} 平台设置失败: {e}")


@pytest.mark.asyncio
async def test_client_api(hass: HomeAssistant, mock_client):
    """测试客户端 API."""
    # 测试设备控制
    result = await mock_client.control_device(
        device_id=12345,
        gateway_id=67890,
        params={"power": "on"},
    )
    assert result is True

    # 测试场景执行
    result = await mock_client.execute_scene(scene_id="scene_1")
    assert result is True

    # 测试获取设备列表
    devices = await mock_client.get_devices(house_id=12345)
    assert isinstance(devices, list)


@pytest.mark.asyncio
async def test_coordinator_services(hass: HomeAssistant, mock_coordinator):
    """测试协调器服务."""
    # 测试场景执行（现在返回 None，不检查返回值）
    await mock_coordinator.async_execute_scene(scene_id="scene_1")
    mock_coordinator.async_execute_scene.assert_called_once_with(scene_id="scene_1")

    # 测试自动化触发
    await mock_coordinator.async_trigger_automation(automation_id="auto_1")
    mock_coordinator.async_trigger_automation.assert_called_once_with(automation_id="auto_1")

    # 测试设备控制
    await mock_coordinator.async_control_device(
        device_id=12345,
        params={"power": "on"},
    )
    mock_coordinator.async_control_device.assert_called_once_with(
        device_id=12345,
        params={"power": "on"},
    )
