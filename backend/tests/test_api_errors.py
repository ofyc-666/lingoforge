"""业务错误响应 helper 测试。

测试 business_error() 稳定错误响应构造，不修改 FastAPI 默认 422。
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.errors import business_error


class TestBusinessError:
    """测试 business_error 返回的 HTTPException 形状和行为。"""

    def test_返回_HTTPException(self) -> None:
        exc = business_error(400, "BAD_REQUEST", "请求参数无效")
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 400

    def test_detail_包含_code_message_details(self) -> None:
        exc = business_error(404, "NOT_FOUND", "用户不存在", {"user_id": 1})
        detail = exc.detail
        assert isinstance(detail, dict)
        assert detail["code"] == "NOT_FOUND"
        assert detail["message"] == "用户不存在"
        assert detail["details"] == {"user_id": 1}

    def test_details_为空时返回空字典(self) -> None:
        exc = business_error(500, "INTERNAL_ERROR", "服务器内部错误")
        assert exc.detail["details"] == {}

    def test_不包含_traceback_或数据库路径(self) -> None:
        exc = business_error(500, "INTERNAL_ERROR", "服务器内部错误")
        detail_str = str(exc.detail)
        assert "traceback" not in detail_str.lower()
        assert ".sqlite" not in detail_str.lower()
        assert "api_key" not in detail_str.lower()
        assert "api key" not in detail_str.lower()

    @pytest.mark.parametrize(
        "status_code,code,message,details",
        [
            (400, "BAD_REQUEST", "参数无效", None),
            (403, "FORBIDDEN", "无权访问", {"resource": "task"}),
            (404, "NOT_FOUND", "资源不存在", {"id": 42}),
            (409, "CONFLICT", "资源冲突", None),
            (500, "INTERNAL_ERROR", "服务器错误", {"trace_id": "abc"}),
        ],
    )
    def test_不同状态码返回正确_shape(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None,
    ) -> None:
        exc = business_error(status_code, code, message, details)
        assert exc.status_code == status_code
        assert exc.detail["code"] == code
        assert exc.detail["message"] == message
        assert exc.detail["details"] == (details or {})

    def test_details_传入空dict_保持为空dict(self) -> None:
        exc = business_error(400, "EMPTY_DETAILS", "空详情", {})
        assert exc.detail["details"] == {}

    def test_SQL关键字不出现在响应中(self) -> None:
        exc = business_error(500, "DB_ERROR", "数据库出错", {"hint": "connection failed"})
        detail_str = str(exc.detail).lower()
        assert "select" not in detail_str
        assert "insert" not in detail_str
        assert "delete" not in detail_str
