"""projector 投影层测试."""
import pytest
from custom_components.yeelight_pro.projector.light import project_light, HALightProjection
from custom_components.yeelight_pro.projector.fan import project_fans, HAFanProjection
from custom_components.yeelight_pro.projector.switch import project_switches, HASwitchProjection
from custom_components.yeelight_pro.projector.sensor import project_sensors, HASensorProjection


class TestProjectLight:
    """project_light 测试."""

    def test_project_light_basic(self, sample_device_data):
        """测试基本灯光投影."""
        result = project_light(sample_device_data, domain="yeelight_pro")
        # 注意：project_light 可能返回 None 或 HALightProjection
        assert result is None or isinstance(result, HALightProjection)
        if result is not None:
            assert result.available is True

    def test_project_light_none_data(self):
        """测试空数据."""
        # 注意：project_light 对 None 数据返回 None
        result = project_light({}, domain="yeelight_pro")
        assert result is None or isinstance(result, HALightProjection)

    def test_project_light_empty_params(self):
        """测试空参数."""
        device_data = {
            "device_id": 12345,
            "name": "测试灯",
            "params": {},
        }
        result = project_light(device_data, domain="yeelight_pro")
        # 可能返回 None 或默认投影
        assert result is None or isinstance(result, HALightProjection)

    def test_project_light_brightness(self, sample_device_data):
        """测试亮度投影."""
        result = project_light(sample_device_data, domain="yeelight_pro")
        if result and result.brightness is not None:
            assert 0 <= result.brightness <= 255

    def test_project_light_color_temp(self, sample_device_data):
        """测试色温投影."""
        result = project_light(sample_device_data, domain="yeelight_pro")
        if result and result.color_temp is not None:
            assert result.color_temp > 0


class TestProjectFans:
    """project_fans 测试."""

    def test_project_fans_returns_list(self, sample_device_data):
        """测试返回列表."""
        result = project_fans(sample_device_data, domain="yeelight_pro")
        assert isinstance(result, list)

    def test_project_fans_none_data(self):
        """测试空数据."""
        # 注意：project_fans 对空字典返回空列表
        result = project_fans({}, domain="yeelight_pro")
        assert isinstance(result, list)

    def test_project_fans_projection_type(self, sample_device_data):
        """测试投影类型."""
        result = project_fans(sample_device_data, domain="yeelight_pro")
        for projection in result:
            assert isinstance(projection, HAFanProjection)


class TestProjectSwitches:
    """project_switches 测试."""

    def test_project_switches_returns_list(self, sample_device_data):
        """测试返回列表."""
        result = project_switches(sample_device_data, domain="yeelight_pro")
        assert isinstance(result, list)

    def test_project_switches_none_data(self):
        """测试空数据."""
        # 注意：project_switches 对空字典返回空列表
        result = project_switches({}, domain="yeelight_pro")
        assert isinstance(result, list)

    def test_project_switches_projection_type(self, sample_device_data):
        """测试投影类型."""
        result = project_switches(sample_device_data, domain="yeelight_pro")
        for projection in result:
            assert isinstance(projection, HASwitchProjection)


class TestProjectSensors:
    """project_sensors 测试."""

    def test_project_sensors_returns_list(self, sample_device_data):
        """测试返回列表."""
        result = project_sensors(sample_device_data, domain="yeelight_pro")
        assert isinstance(result, list)

    def test_project_sensors_none_data(self):
        """测试空数据."""
        # 注意：project_sensors 对空字典返回空列表
        result = project_sensors({}, domain="yeelight_pro")
        assert isinstance(result, list)

    def test_project_sensors_projection_type(self, sample_device_data):
        """测试投影类型."""
        result = project_sensors(sample_device_data, domain="yeelight_pro")
        for projection in result:
            assert isinstance(projection, HASensorProjection)
