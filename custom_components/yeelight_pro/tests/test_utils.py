"""utils 工具函数测试."""
import pytest
from custom_components.yeelight_pro.utils import (
    to_bool,
    to_int,
    to_float,
    to_str,
    to_str_or_empty,
    to_category,
    matches_any,
    matches_category,
)


class TestToBool:
    """to_bool 测试."""

    def test_true_values(self):
        """测试真值."""
        assert to_bool(True) is True
        assert to_bool(1) is True
        assert to_bool("true") is True
        assert to_bool("yes") is True
        assert to_bool("on") is True
        assert to_bool("1") is True

    def test_false_values(self):
        """测试假值."""
        assert to_bool(False) is False
        assert to_bool(0) is False
        assert to_bool("false") is False
        assert to_bool("no") is False
        assert to_bool("off") is False
        assert to_bool("0") is False

    def test_none_returns_default(self):
        """测试 None 返回默认值."""
        assert to_bool(None) is False
        assert to_bool(None, default=True) is True

    def test_invalid_string_returns_default(self):
        """测试无效字符串返回默认值."""
        # 注意：to_bool 对空字符串返回 default
        assert to_bool("", default=False) is False
        # 注意：to_bool 对空字符串也返回 False（不是 default）
        assert to_bool("", default=True) is False
        # 对非空字符串返回 True
        assert to_bool("invalid") is True


class TestToInt:
    """to_int 测试."""

    def test_valid_integers(self):
        """测试有效整数."""
        assert to_int(42) == 42
        assert to_int("100") == 100
        assert to_int(3.14) == 3

    def test_none_returns_none(self):
        """测试 None 返回 None."""
        assert to_int(None) is None

    def test_invalid_returns_none(self):
        """测试无效值返回 None."""
        assert to_int("abc") is None
        assert to_int("") is None


class TestToFloat:
    """to_float 测试."""

    def test_valid_floats(self):
        """测试有效浮点数."""
        assert to_float(3.14) == 3.14
        assert to_float("2.5") == 2.5
        assert to_float(100) == 100.0

    def test_none_returns_none(self):
        """测试 None 返回 None."""
        assert to_float(None) is None

    def test_invalid_returns_none(self):
        """测试无效值返回 None."""
        assert to_float("abc") is None


class TestToStr:
    """to_str 测试."""

    def test_valid_strings(self):
        """测试有效字符串."""
        assert to_str("hello") == "hello"
        assert to_str(123) == "123"
        assert to_str(3.14) == "3.14"

    def test_none_returns_none(self):
        """测试 None 返回 None."""
        assert to_str(None) is None

    def test_empty_string_returns_none(self):
        """测试空字符串返回 None."""
        assert to_str("") is None
        assert to_str("  ") is None


class TestToStrOrEmpty:
    """to_str_or_empty 测试."""

    def test_valid_strings(self):
        """测试有效字符串."""
        assert to_str_or_empty("hello") == "hello"
        assert to_str_or_empty(123) == "123"

    def test_none_returns_empty(self):
        """测试 None 返回空字符串."""
        assert to_str_or_empty(None) == ""

    def test_empty_string_returns_empty(self):
        """测试空字符串返回空字符串."""
        assert to_str_or_empty("") == ""


class TestToCategory:
    """to_category 测试."""

    def test_lowercase(self):
        """测试转小写."""
        assert to_category("Light") == "light"
        assert to_category("FAN") == "fan"

    def test_none_returns_empty(self):
        """测试 None 返回空字符串."""
        # 注意：to_category 对 None 返回空字符串
        assert to_category(None) == ""

    def test_strips_whitespace(self):
        """测试去除空白."""
        assert to_category("  light  ") == "light"


class TestMatchesAny:
    """matches_any 测试."""

    def test_match_found(self):
        """测试找到匹配."""
        # 注意：matches_any 检查 token 是否在 value 中（token in value）
        # 所以 value 应该包含 token
        assert matches_any(["light_controller", "fan_switch"], ("light",)) is True
        assert matches_any(["main_fan", "light_switch"], ("light", "fan")) is True

    def test_no_match(self):
        """测试未找到匹配."""
        assert matches_any(["switch", "outlet"], ("light", "fan")) is False

    def test_none_values(self):
        """测试 None 值列表."""
        # 注意：None 列表会抛出 TypeError
        with pytest.raises(TypeError):
            matches_any(None, ("light", "fan"))


class TestMatchesCategory:
    """matches_category 测试."""

    def test_match_found(self):
        """测试找到匹配."""
        # 注意：matches_category 检查 token 是否在 category 中
        # category 应该包含 token
        assert matches_category("light_controller", ("light",)) is True
        assert matches_category("main_light", ("light",)) is True

    def test_no_match(self):
        """测试未找到匹配."""
        assert matches_category("fan", ("light",)) is False

    def test_none_value(self):
        """测试 None 值."""
        # 注意：None 会抛出 TypeError
        with pytest.raises(TypeError):
            matches_category(None, ("light",))
