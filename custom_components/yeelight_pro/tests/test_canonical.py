"""canonical 模型层测试."""
from custom_components.yeelight_pro.canonical.models import (
    ActionParamModel,
    ComponentModel,
    HADeviceInstanceModel,
    HAProductModel,
    PropertyModel,
    ValueItemModel,
    ValueRangeModel,
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

    def test_from_dict_normalizes_numeric_values(self):
        """测试范围值会收敛为 int 或 None."""
        data = {"min": "2700", "max": 6500.9, "step": ""}
        model = ValueRangeModel.from_dict(data)
        assert model.min == 2700
        assert model.max == 6500
        assert model.step is None

    def test_from_dict_with_invalid_range_values(self):
        """测试全非法范围值返回 None."""
        assert ValueRangeModel.from_dict({"min": "bad", "max": None, "step": ""}) is None

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
        data = {"code": " warm ", "desc": "暖白"}
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
            "unit": "k",
            "zoom": "-1",
            "scale": "10",
            "value_range": {"min": 0, "max": 100, "step": 1},
            "value_list": [{"code": "low", "desc": "低"}],
        }
        model = PropertyModel.from_dict(data)
        assert model.prop_id == "brightness"
        assert model.name == "亮度"
        assert model.property_type == "integer"
        assert model.unit == "K"
        assert model.zoom == -1
        assert model.scale == 10
        assert model.value_range.min == 0
        assert len(model.value_list) == 1
        assert model.value_list[0].code == "low"

    def test_from_dict_normalizes_value_list(self):
        """测试属性枚举列表过滤空 code 并去重."""
        model = PropertyModel.from_dict(
            {
                "prop_id": "mode",
                "value_list": [
                    {"code": " 1 ", "desc": "Auto"},
                    {"code": "", "desc": "Empty"},
                    {"desc": "Missing"},
                    {"code": 2, "desc": "Cool"},
                    {"code": "2", "desc": "Duplicate cool"},
                ],
            }
        )

        assert [(item.code, item.desc) for item in model.value_list] == [
            ("1", "Auto"),
            ("2", "Cool"),
        ]

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


class TestActionParamModel:
    """ActionParamModel 测试."""

    def test_from_dict_normalizes_unit(self):
        """测试动作参数单位归一化."""
        model = ActionParamModel.from_dict(
            {
                "prop_id": "ct",
                "unit": "kelvin",
                "zoom": "bad",
                "scale": 0,
                "value_list": [
                    {"code": "0", "desc": "Forward"},
                    {"code": "0", "desc": "Duplicate"},
                ],
            }
        )
        assert model.prop_id == "ct"
        assert model.unit == "K"
        assert model.zoom == 1
        assert model.scale == 1
        assert [(item.code, item.desc) for item in model.value_list] == [
            ("0", "Forward")
        ]


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
            "components": [
                {
                    "component_id": "light",
                    "properties": [{"prop_id": "ct", "zoom": -1, "scale": 10}],
                }
            ],
        }
        model = HAProductModel.from_dict(data)
        result = model.to_dict()
        assert "product" in result
        assert "components" in result
        prop = result["components"][0]["properties"][0]
        assert prop["zoom"] == -1
        assert prop["scale"] == 10


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
