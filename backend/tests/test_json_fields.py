"""SQLite JSON 字段工具测试。"""

from __future__ import annotations

import pytest

from app.storage.json_fields import from_json_text, to_json_text


class TestToJsonText:
    """to_json_text 测试。"""

    def test_dict_to_json_text(self):
        result = to_json_text({"key": "value"})
        assert '"key"' in result
        assert '"value"' in result

    def test_list_to_json_text(self):
        result = to_json_text([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_string_to_json_text(self):
        assert to_json_text("hello") == '"hello"'

    def test_int_to_json_text(self):
        assert to_json_text(42) == "42"

    def test_float_to_json_text(self):
        result = to_json_text(3.14)
        assert result.startswith("3.14")

    def test_bool_to_json_text(self):
        assert to_json_text(True) == "true"
        assert to_json_text(False) == "false"

    def test_none_to_json_text(self):
        assert to_json_text(None) == "null"

    def test_chinese_not_escaped(self):
        result = to_json_text({"姓名": "张三"})
        assert "姓名" in result
        assert "张三" in result
        assert "\\u" not in result

    def test_stable_output(self):
        a = to_json_text({"b": 2, "a": 1})
        b = to_json_text({"b": 2, "a": 1})
        assert a == b

    def test_nested_structures(self):
        value = {"items": [{"id": 1, "tags": ["a", "b"]}]}
        result = to_json_text(value)
        assert "items" in result
        assert '"a"' in result


class TestFromJsonText:
    """from_json_text 测试。"""

    def test_parse_dict(self):
        result = from_json_text('{"key": "value"}', None)
        assert result == {"key": "value"}

    def test_parse_list(self):
        result = from_json_text('[1, 2, 3]', None)
        assert result == [1, 2, 3]

    def test_parse_chinese(self):
        result = from_json_text('{"姓名": "张三"}', None)
        assert result == {"姓名": "张三"}

    def test_empty_string_returns_default(self):
        assert from_json_text("", "fallback") == "fallback"

    def test_none_text_returns_default(self):
        assert from_json_text(None, "fallback") == "fallback"

    def test_invalid_json_returns_default(self):
        assert from_json_text("{invalid}", []) == []

    def test_truncated_json_returns_default(self):
        assert from_json_text('{"key":', None) is None

    def test_default_none(self):
        # 空字符串时返回 None
        assert from_json_text("", None) is None

    def test_null_json_value(self):
        # JSON "null" 是合法值，应返回 None
        result = from_json_text("null", "default")
        assert result is None

    def test_parse_int(self):
        assert from_json_text("42", None) == 42

    def test_parse_float(self):
        assert from_json_text("3.14", None) == 3.14

    def test_parse_bool(self):
        assert from_json_text("true", None) is True
        assert from_json_text("false", None) is False

    def test_parse_nested_array(self):
        result = from_json_text('[{"id": 1}, {"id": 2}]', None)
        assert result == [{"id": 1}, {"id": 2}]
