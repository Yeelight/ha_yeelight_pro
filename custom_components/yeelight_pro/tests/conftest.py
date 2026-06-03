"""Yeelight Pro 集成测试套件.

测试覆盖：
- canonical 模型层
- adapters 适配器层
- converter 转换层
- projector 投影层
- core 核心层
- utils 工具函数
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN


@pytest.fixture
def mock_hass():
    """创建模拟的 Home Assistant 实例."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    return hass


@pytest.fixture
def mock_config_entry():
    """创建模拟的配置条目."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "connection_mode": "cloud",
        "access_token": "test_token",
        "house_id": 12345,
        "cloud_domain": "api.yeelight.com",
    }
    return entry


@pytest.fixture
def mock_coordinator():
    """创建模拟的协调器."""
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.client = MagicMock()
    coordinator.house_id = 12345
    # 辅助数据直接挂载在 coordinator 上
    coordinator.scenes = []
    coordinator.automations = []
    coordinator.groups = []
    coordinator.rooms = []
    coordinator.async_execute_scene = AsyncMock()
    coordinator.async_trigger_automation = AsyncMock()
    coordinator.async_control_device = AsyncMock()
    coordinator.async_control_group = AsyncMock()
    return coordinator


@pytest.fixture
def sample_device_data():
    """示例设备数据."""
    return {
        "device_id": 12345,
        "name": "客厅灯",
        "model_id": "YLCT01",
        "online": True,
        "params": {
            "power": "on",
            "brightness": 80,
            "color_temperature": 4000,
        },
        "ha_device_instance": {
            "device_info": {
                "identifiers": [["yeelight_pro", "12345"]],
                "name": "客厅灯",
                "manufacturer": "Yeelight",
                "model": "YLCT01",
            },
            "component_instances": {
                "light": {
                    "available": True,
                    "params": {
                        "power": "on",
                        "brightness": 80,
                        "color_temperature": 4000,
                    },
                },
            },
        },
    }


@pytest.fixture
def sample_scene_data():
    """示例场景数据."""
    return [
        {"id": "scene_1", "name": "回家模式", "icon": "mdi:home"},
        {"id": "scene_2", "name": "离家模式", "icon": "mdi:home-export-outline"},
    ]


@pytest.fixture
def sample_automation_data():
    """示例自动化数据."""
    return [
        {
            "id": "auto_1",
            "name": "日落自动开灯",
            "type": "sensor",
            "enabled": True,
        },
        {
            "id": "auto_2",
            "name": "定时关灯",
            "type": "timer",
            "enabled": False,
        },
    ]


@pytest.fixture
def sample_group_data():
    """示例灯组数据."""
    return [
        {
            "id": "group_1",
            "name": "客厅灯组",
            "device_ids": [12345, 12346],
        },
    ]


@pytest.fixture
def sample_room_data():
    """示例房间数据."""
    return [
        {"id": "room_1", "name": "客厅"},
        {"id": "room_2", "name": "卧室"},
    ]
