"""canonical 模型层测试."""
import pytest
from custom_components.yeelight_pro.canonical.models import (
    HAProductModel,
    HADeviceInstanceModel,
    ComponentModel,
    PropertyModel,
    ValueRangeModel,
    ValueItemModel,
)


class TestValueRangeModel:
    """ValueRangeModel 测试."""

    def test_from_dict_with_valid_data(self):
        """测试从有效字典创建."""
        data = {"min": 0, "max": 100, "step": 1}
        model = ValueRangeModel.from_dict(data)
        assert model.min == 0
        assert model.max == 100
        assert model.step == 1

    def test_from_dict_with_none(self):
        """测试从 None 创建返回 None."""
        assert ValueRangeModel.from_dict(None) is None

    def test_from_dict_with_empty_dict(self):
        """测试从空字典创建."""
        # 注意：from_dict({}) 返回 None
        result = ValueRangeModel.from_dict({})
        assert result is None


class TestValueItemModel:
    """ValueItemModel 测试."""

    def test_from_dict(self):
        """测试从字典创建."""
        data = {"code": "warm", "desc": "暖白"}
        model = ValueItemModel.from_dict(data)
        assert model.code == "warm"
        assert model.desc == "暖白"

    def test_from_dict_without_desc(self):
        """测试没有 desc 字段."""
        data = {"code": "cool"}
        model = ValueItemModel.from_dict(data)
        assert model.code == "cool"
        assert model.desc is None


class TestPropertyModel:
    """PropertyModel 测试."""

    def test_from_dict_with_full_data(self):
        """测试完整数据."""
        data = {
            "prop_id": "brightness",
            "name": "亮度",
            "property_type": "integer",
            "value_range": {"min": 0, "max": 100, "step": 1},
            "value_list": [{"code": "low", "desc": "低"}],
        }
        model = PropertyModel.from_dict(data)
        assert model.prop_id == "brightness"
        assert model.name == "亮度"
        assert model.property_type == "integer"
        assert model.value_range.min == 0
        assert len(model.value_list) == 1

    def test_from_dict_with_propId_alias(self):
        """测试 propId 别名."""
        data = {"propId": "power", "name": "电源"}
        model = PropertyModel.from_dict(data)
        assert model.prop_id == "power"

    def test_from_dict_minimal(self):
        """测试最小数据."""
        data = {"prop_id": "switch"}
        model = PropertyModel.from_dict(data)
        assert model.prop_id == "switch"
        assert model.name is None


class TestComponentModel:
    """ComponentModel 测试."""

    def test_from_dict_with_properties(self):
        """测试包含属性的组件."""
        data = {
            "component_id": "light",
            "name": "灯光",
            "properties": [
                {"prop_id": "power", "name": "电源"},
                {"prop_id": "brightness", "name": "亮度"},
            ],
        }
        model = ComponentModel.from_dict(data)
        assert model.component_id == "light"
        assert len(model.properties) == 2

    def test_from_dict_empty(self):
        """测试空组件."""
        data = {"component_id": "switch"}
        model = ComponentModel.from_dict(data)
        assert model.component_id == "switch"
        assert len(model.properties) == 0
        assert len(model.events) == 0
        assert len(model.actions) == 0


class TestHAProductModel:
    """HAProductModel 测试."""

    def test_from_dict(self):
        """测试从字典创建."""
        data = {
            "product": {
                "model_id": "YLCT01",
                "name": "Yeelight 灯泡",
            },
            "components": [
                {"component_id": "light"},
            ],
        }
        model = HAProductModel.from_dict(data)
        assert model.product.model_id == "YLCT01"
        assert len(model.components) == 1

    def test_to_dict(self):
        """测试转换为字典."""
        data = {
            "product": {"model_id": "YLCT01"},
            "components": [],
        }
        model = HAProductModel.from_dict(data)
        result = model.to_dict()
        assert "product" in result
        assert "components" in result


class TestHADeviceInstanceModel:
    """HADeviceInstanceModel 测试."""

    def test_from_dict(self):
        """测试从字典创建."""
        data = {
            "device_info": {
                "identifiers": [["yeelight_pro", "12345"]],
                "name": "客厅灯",
            },
            "components": [
                {
                    "component_id": "light",
                    "available": True,
                    "params": {"power": "on"},
                },
            ],
        }
        model = HADeviceInstanceModel.from_dict(data)
        assert model.device_info.identifiers == [["yeelight_pro", "12345"]]
        assert len(model.components) == 1

    def test_to_dict(self):
        """测试转换为字典."""
        data = {
            "device_info": {"name": "test"},
            "components": [],
        }
        model = HADeviceInstanceModel.from_dict(data)
        result = model.to_dict()
        assert "device_info" in result
        assert "components" in result
