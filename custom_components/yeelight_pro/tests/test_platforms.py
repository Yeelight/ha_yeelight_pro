"""平台实体测试."""
import pytest

from homeassistant.components.light import ATTR_TRANSITION, LightEntity
from homeassistant.components.fan import FanEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity

from custom_components.yeelight_pro.light import ATTR_COLOR_TEMP_KELVIN, YeelightProLight
from custom_components.yeelight_pro.fan import YeelightProFan
from custom_components.yeelight_pro.switch import YeelightProSwitch
from custom_components.yeelight_pro.sensor import YeelightProSensor
from custom_components.yeelight_pro.const import DOMAIN

from .projection_helpers import projection_payload


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

    def test_main_light_suggests_friendly_entity_object_id(self, mock_coordinator):
        """主灯实体首次注册时应使用设备名生成 entity_id."""
        payload = projection_payload(
            device_id="304784333",
            category="light",
            component_id="main_light",
            component_category="color temperature light",
            state={"p": True, "l": 80, "ct": 4000},
        )
        payload["name"] = "厨房操作台灯"
        payload["ha_device_instance"]["name"] = "厨房操作台灯"
        payload["ha_device_instance"]["device_info"]["name"] = "厨房操作台灯"
        mock_coordinator.get_device.return_value = payload

        light = YeelightProLight(mock_coordinator, 304784333)

        assert light.name is None
        assert light.suggested_object_id == "厨房操作台灯"

    @pytest.mark.asyncio
    async def test_turn_on_ignores_color_temp_for_rgb_only_light(self, mock_coordinator):
        """无色温彩光灯被误传色温时，不应向设备下发 ct。"""
        payload = projection_payload(
            device_id="12345",
            category="light",
            component_id="main_light",
            component_category="color light without temperature",
            state={"p": True, "l": 60, "c": 0x112233},
        )
        mock_coordinator.get_device.return_value = payload
        light = YeelightProLight(mock_coordinator, 12345)

        await light.async_turn_on(**{ATTR_COLOR_TEMP_KELVIN: 4000})

        mock_coordinator.async_control_device.assert_awaited_once_with(
            12345,
            {"p": True},
        )

    @pytest.mark.asyncio
    async def test_turn_on_keeps_color_temp_for_supported_light(self, mock_coordinator):
        """支持色温的灯仍应下发 ct，并按默认范围钳制。"""
        payload = projection_payload(
            device_id="12345",
            category="light",
            component_id="main_light",
            component_category="color temperature light",
            state={"p": True, "l": 60, "ct": 3000},
        )
        mock_coordinator.get_device.return_value = payload
        light = YeelightProLight(mock_coordinator, 12345)

        await light.async_turn_on(**{ATTR_COLOR_TEMP_KELVIN: 7000})

        mock_coordinator.async_control_device.assert_awaited_once_with(
            12345,
            {"p": True, "ct": 6500},
        )

    @pytest.mark.asyncio
    async def test_turn_on_passes_transition_duration(self, mock_coordinator):
        """HA light.turn_on transition 应转换成易来 duration 毫秒。"""
        payload = projection_payload(
            device_id="12345",
            category="light",
            component_id="main_light",
            component_category="color temperature light",
            state={"p": False, "l": 60, "ct": 3000},
        )
        mock_coordinator.get_device.return_value = payload
        light = YeelightProLight(mock_coordinator, 12345)

        await light.async_turn_on(**{ATTR_TRANSITION: 2.5})

        mock_coordinator.async_control_device.assert_awaited_once_with(
            12345,
            {"p": True},
            duration=2500,
        )

    @pytest.mark.asyncio
    async def test_turn_off_passes_transition_duration(self, mock_coordinator):
        """HA light.turn_off transition 应复用相同 duration 语义。"""
        payload = projection_payload(
            device_id="12345",
            category="light",
            component_id="main_light",
            component_category="color temperature light",
            state={"p": True, "l": 60, "ct": 3000},
        )
        mock_coordinator.get_device.return_value = payload
        light = YeelightProLight(mock_coordinator, 12345)

        await light.async_turn_off(**{ATTR_TRANSITION: 1})

        mock_coordinator.async_control_device.assert_awaited_once_with(
            12345,
            {"p": False},
            duration=1000,
        )


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
            component_id="fresh_air",
        )
        assert fan._device_id == 12345
        assert fan._component_id == "fresh_air"


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

    def test_switch_suggests_device_and_channel_object_id(self, mock_coordinator):
        """多键开关 entity_id 建议应包含设备名和友好通道名."""
        payload = projection_payload(
            device_id="304784336",
            category="relay_switch",
            component_id="switch_1",
            component_category="switch control",
            state={"p": True},
            params={"1-p": True, "2-p": False},
        )
        payload["pid"] = 854018
        payload["name"] = "厨房智能开关"
        payload["ha_device_instance"]["name"] = "厨房智能开关"
        payload["ha_device_instance"]["device_info"]["name"] = "厨房智能开关"
        mock_coordinator.get_device.return_value = payload

        switch = YeelightProSwitch(
            mock_coordinator,
            304784336,
            component_id="switch_1",
        )

        assert switch.name == "左键"
        assert switch.suggested_object_id == "厨房智能开关 左键"


class TestYeelightProSensor:
    """YeelightProSensor 测试."""

    def test_inheritance(self):
        """测试继承关系."""
        assert issubclass(YeelightProSensor, SensorEntity)

    def test_init(self, mock_coordinator, sample_device_data):
        """测试初始化."""
        mock_coordinator.data = {12345: sample_device_data}
        sensor = YeelightProSensor(
            mock_coordinator,
            12345,
            component_id="temperature",
        )
        assert sensor._device_id == 12345
        assert sensor._component_id == "temperature"

    def test_power_meter_device_class_and_state_class(self, mock_coordinator):
        """电量 sensor 应暴露 HA 统计语义."""
        mock_coordinator.hide_unknown_entities = True
        mock_coordinator.data = {
            12345: {
                "id": 12345,
                "device_id": 12345,
                "name": "Power meter",
                "category": "other",
                "type": "sensor",
                "online": True,
                "params": {},
                "ha_device_instance": {
                    "device_id": "12345",
                    "name": "Power meter",
                    "online": True,
                    "device_info": {
                        "identifiers": [["yeelight_pro", "12345"]],
                        "manufacturer": "Yeelight",
                        "model": "other",
                        "name": "Power meter",
                    },
                    "components": [
                        {
                            "component_id": "power_meter",
                            "category": "power meter",
                            "available": True,
                            "state": {"curp": 18, "iec": 250},
                        }
                    ],
                },
            }
        }
        mock_coordinator.get_device.return_value = mock_coordinator.data[12345]

        power = YeelightProSensor(
            mock_coordinator,
            12345,
            component_id="current_power",
        )
        energy = YeelightProSensor(
            mock_coordinator,
            12345,
            component_id="energy_consumption",
        )

        assert power.device_class == SensorDeviceClass.POWER
        assert power.native_unit_of_measurement == "W"
        assert power.state_class == SensorStateClass.MEASUREMENT
        assert energy.device_class == SensorDeviceClass.ENERGY
        assert energy.native_unit_of_measurement == "Wh"
        assert energy.state_class == SensorStateClass.TOTAL_INCREASING

    def test_dali_voltage_sensors_use_ha_voltage_units(self, mock_coordinator):
        """DALI 电压原始值单位为 0.1V，HA sensor 应显示为 V。"""
        mock_coordinator.hide_unknown_entities = True
        mock_coordinator.data = {
            12345: {
                "id": 12345,
                "device_id": 12345,
                "name": "DALI energy",
                "category": "other",
                "type": "sensor",
                "online": True,
                "params": {},
                "ha_device_instance": {
                    "device_id": "12345",
                    "name": "DALI energy",
                    "online": True,
                    "device_info": {
                        "identifiers": [["yeelight_pro", "12345"]],
                        "manufacturer": "Yeelight",
                        "model": "other",
                        "name": "DALI energy",
                    },
                    "components": [
                        {
                            "component_id": "dali_energy",
                            "category": "dali energy",
                            "available": True,
                            "state": {"esv": 2200, "lsv": 360},
                        }
                    ],
                },
            }
        }
        mock_coordinator.get_device.return_value = mock_coordinator.data[12345]

        external_voltage = YeelightProSensor(
            mock_coordinator,
            12345,
            component_id="external_supply_voltage",
        )
        light_voltage = YeelightProSensor(
            mock_coordinator,
            12345,
            component_id="light_source_voltage",
        )

        assert external_voltage.native_value == 220
        assert external_voltage.device_class == SensorDeviceClass.VOLTAGE
        assert external_voltage.native_unit_of_measurement == "V"
        assert external_voltage.state_class == SensorStateClass.MEASUREMENT
        assert light_voltage.native_value == 36
        assert light_voltage.device_class == SensorDeviceClass.VOLTAGE
        assert light_voltage.native_unit_of_measurement == "V"

    def test_dali_energy_device_class_and_state_class(self, mock_coordinator):
        """dali能量组件的 ap/ae 应暴露 HA 统计语义。"""
        mock_coordinator.hide_unknown_entities = True
        mock_coordinator.data = {
            12345: {
                "id": 12345,
                "device_id": 12345,
                "name": "DALI energy",
                "category": "other",
                "type": "sensor",
                "online": True,
                "params": {},
                "ha_device_instance": {
                    "device_id": "12345",
                    "name": "DALI energy",
                    "online": True,
                    "device_info": {
                        "identifiers": [["yeelight_pro", "12345"]],
                        "manufacturer": "Yeelight",
                        "model": "other",
                        "name": "DALI energy",
                    },
                    "components": [
                        {
                            "component_id": "dali_energy",
                            "category": "dali energy",
                            "available": True,
                            "state": {"ap": 19, "ae": 880},
                        }
                    ],
                },
            }
        }
        mock_coordinator.get_device.return_value = mock_coordinator.data[12345]

        power = YeelightProSensor(
            mock_coordinator,
            12345,
            component_id="active_power",
        )
        energy = YeelightProSensor(
            mock_coordinator,
            12345,
            component_id="active_energy",
        )

        assert power.device_class == SensorDeviceClass.POWER
        assert power.native_unit_of_measurement == "W"
        assert power.state_class == SensorStateClass.MEASUREMENT
        assert energy.device_class == SensorDeviceClass.ENERGY
        assert energy.native_unit_of_measurement == "Wh"
        assert energy.state_class == SensorStateClass.TOTAL_INCREASING
