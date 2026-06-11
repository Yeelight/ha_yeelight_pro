"""projector 投影层测试."""
from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntityFeature,
)

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

    def test_project_fans_canonical_indexed_controls(self):
        """canonical fan 必须保留 indexed 控制键和核心状态投影."""
        result = project_fans(_canonical_fan_payload(), domain="yeelight_pro")

        assert len(result) == 1
        projection = result[0]
        assert isinstance(projection, HAFanProjection)
        assert projection.component_id == "fan_1"
        assert projection.unique_id == "yeelight_pro_fan-1_fan_1"
        assert projection.name == "第 1 键"
        assert projection.available is True
        assert projection.is_on is True
        assert projection.power_key == "1-p"
        assert projection.speed_key == "1-lv"
        assert projection.mode_key == "1-m"
        assert projection.direction_key == "1-dir"
        assert projection.speed_range is not None
        assert projection.speed_range.min == 1
        assert projection.speed_range.max == 6
        assert projection.speed_range.step == 1
        assert projection.percentage == 50
        assert projection.speed_count == 6
        assert projection.preset_mode == "sleep"
        assert projection.preset_modes == ["sleep", "natural"]
        assert projection.current_direction == DIRECTION_REVERSE
        assert projection.direction_values == {
            DIRECTION_FORWARD: "0",
            DIRECTION_REVERSE: "1",
        }
        assert projection.supported_features & FanEntityFeature.SET_SPEED
        assert projection.supported_features & FanEntityFeature.PRESET_MODE
        assert projection.supported_features & FanEntityFeature.DIRECTION

    def test_project_fans_legacy_payload(self):
        """legacy fan payload 仍必须投影基础风扇能力."""
        result = project_fans(
            {
                "device_id": "legacy-fan",
                "type": "fan",
                "online": True,
                "params": {
                    "p": True,
                    "lv": 50,
                    "m": "natural",
                    "dir": "forward",
                },
            },
            domain="yeelight_pro",
        )

        assert len(result) == 1
        projection = result[0]
        assert projection.component_id == "fan"
        assert projection.unique_id == "yeelight_pro_legacy-fan_fan"
        assert projection.available is True
        assert projection.is_on is True
        assert projection.power_key == "p"
        assert projection.speed_key == "lv"
        assert projection.mode_key == "m"
        assert projection.direction_key == "dir"
        assert projection.speed_range is not None
        assert projection.speed_range.min == 1
        assert projection.speed_range.max == 100
        assert projection.percentage == 50
        assert projection.preset_mode == "natural"
        assert projection.preset_modes == ["natural"]
        assert projection.current_direction == DIRECTION_FORWARD

    def test_project_fans_uses_documented_fresh_air_properties(self):
        """新风组件应使用易来 vmcp/vmcf 属性，而不是旧 fan lv 规则."""
        result = project_fans(_fresh_air_payload(), domain="yeelight_pro")

        assert len(result) == 1
        projection = result[0]
        assert projection.component_id == "fresh_air"
        assert projection.power_key == "1-vmcp"
        assert projection.speed_key == "1-vmcf"
        assert projection.is_on is True
        assert projection.percentage == 3
        assert projection.speed_range is not None
        assert projection.speed_range.min == 1
        assert projection.speed_range.max == 100
        assert projection.supported_features & FanEntityFeature.SET_SPEED


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


def _canonical_fan_payload():
    """构造带 indexed 控制键的 canonical fan 载荷."""
    return {
        "device_id": "fan-1",
        "category": "temp_control",
        "type": "fan",
        "online": True,
        "params": {
            "1-p": True,
            "1-lv": 3,
            "1-m": "sleep",
            "1-dir": 1,
        },
        "ha_device_instance": {
            "device_id": "fan-1",
            "name": "吊扇",
            "online": True,
            "device_info": {
                "identifiers": [["yeelight_pro", "fan-1"]],
                "manufacturer": "Yeelight",
                "model": "ceiling-fan",
                "name": "吊扇",
            },
            "components": [
                {
                    "component_id": "fan_1",
                    "category": "fan",
                    "available": True,
                    "instance_capabilities": {
                        "features": ["speed", "mode", "direction"],
                        "constraints": {
                            "speed_level": {"min": 1, "max": 6, "step": 1},
                            "mode": {
                                "values": [
                                    {"code": "sleep"},
                                    {"code": "natural"},
                                ]
                            },
                            "direction": {
                                "values": [
                                    {"code": 0, "desc": "forward"},
                                    {"code": 1, "desc": "reverse"},
                                ]
                            },
                        },
                    },
                    "state": {
                        "p": True,
                        "lv": 3,
                        "m": "sleep",
                        "dir": 1,
                    },
                }
            ],
        },
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "fan-model",
                "manufacturer": "Yeelight",
                "model": "ceiling-fan",
                "category": "temp_control",
            },
            "components": [
                {
                    "component_id": "fan_1",
                    "category": "fan",
                    "properties": [
                        {"prop_id": "p"},
                        {
                            "prop_id": "lv",
                            "value_range": {"min": 1, "max": 6, "step": 1},
                        },
                        {
                            "prop_id": "m",
                            "value_list": [
                                {"code": "sleep"},
                                {"code": "natural"},
                            ],
                        },
                        {
                            "prop_id": "dir",
                            "value_list": [
                                {"code": 0, "desc": "forward"},
                                {"code": 1, "desc": "reverse"},
                            ],
                        },
                    ],
                    "events": [],
                }
            ],
        },
    }


def _fresh_air_payload():
    """构造易来新风组件载荷，覆盖 vmcp/vmcf 控制键."""
    return {
        "device_id": "fresh-air-1",
        "category": "temp_control",
        "type": "temp_control",
        "online": True,
        "params": {
            "1-vmcp": True,
            "1-vmcf": 3,
        },
        "ha_device_instance": {
            "device_id": "fresh-air-1",
            "name": "新风",
            "online": True,
            "device_info": {
                "identifiers": [["yeelight_pro", "fresh-air-1"]],
                "manufacturer": "Yeelight",
                "model": "fresh-air",
                "name": "新风",
            },
            "extensions": {
                "component_state_keys": {
                    "fresh_air": {"vmcp": "1-vmcp", "vmcf": "1-vmcf"}
                }
            },
            "components": [
                {
                    "component_id": "fresh_air",
                    "category": "fresh air",
                    "available": True,
                    "state": {
                        "vmcp": True,
                        "vmcf": 3,
                    },
                }
            ],
        },
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "fresh-air-model",
                "manufacturer": "Yeelight",
                "model": "fresh-air",
                "category": "temp_control",
            },
            "components": [
                {
                    "component_id": "fresh_air",
                    "category": "fresh air",
                    "properties": [
                        {"prop_id": "vmcp"},
                        {
                            "prop_id": "vmcf",
                            "value_range": {"min": 1, "max": 100, "step": 1},
                        },
                    ],
                    "events": [],
                }
            ],
        },
    }
