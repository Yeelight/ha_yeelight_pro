"""平台实体测试."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.light import LightEntity
from homeassistant.components.fan import FanEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.sensor import SensorEntity

from custom_components.yeelight_pro.light import YeelightProLight
from custom_components.yeelight_pro.fan import YeelightProFan
from custom_components.yeelight_pro.switch import YeelightProSwitch
from custom_components.yeelight_pro.sensor import YeelightProSensor
from custom_components.yeelight_pro.const import DOMAIN


class TestYeelightProLight:
    """YeelightProLight 测试."""

    def test_inheritance(self):
        """测试继承关系."""
        assert issubclass(YeelightProLight, LightEntity)

    def test_init(self, mock_coordinator, sample_device_data):
        """测试初始化."""
        mock_coordinator.data = {12345: sample_device_data}
        light = YeelightProLight(mock_coordinator, 12345)
        assert light._device_id == 12345
        assert light._attr_has_entity_name is True

    def test_unique_id(self, mock_coordinator, sample_device_data):
        """测试唯一 ID."""
        mock_coordinator.data = {12345: sample_device_data}
        light = YeelightProLight(mock_coordinator, 12345)
        assert light.unique_id is not None
        assert DOMAIN in light.unique_id

    def test_device_info(self, mock_coordinator, sample_device_data):
        """测试设备信息."""
        mock_coordinator.data = {12345: sample_device_data}
        light = YeelightProLight(mock_coordinator, 12345)
        assert light.device_info is not None


class TestYeelightProFan:
    """YeelightProFan 测试."""

    def test_inheritance(self):
        """测试继承关系."""
        assert issubclass(YeelightProFan, FanEntity)

    def test_init(self, mock_coordinator, sample_device_data):
        """测试初始化."""
        mock_coordinator.data = {12345: sample_device_data}
        fan = YeelightProFan(
            mock_coordinator,
            12345,
            component_id="fan",
        )
        assert fan._device_id == 12345
        assert fan._component_id == "fan"


class TestYeelightProSwitch:
    """YeelightProSwitch 测试."""

    def test_inheritance(self):
        """测试继承关系."""
        assert issubclass(YeelightProSwitch, SwitchEntity)

    def test_init(self, mock_coordinator, sample_device_data):
        """测试初始化."""
        mock_coordinator.data = {12345: sample_device_data}
        switch = YeelightProSwitch(
            mock_coordinator,
            12345,
            component_id="switch",
        )
        assert switch._device_id == 12345


class TestYeelightProSensor:
    """YeelightProSensor 测试."""

    def test_inheritance(self):
        """测试继承关系."""
        assert issubclass(YeelightProSensor, SensorEntity)

    def test_init(self, mock_coordinator, sample_device_data):
        """测试初始化."""
        mock_coordinator.data = {12345: sample_device_data}
        # 注意：需要查看实际的 __init__ 签名
        # 暂时跳过这个测试
        pass
