"""稳定的业务错误响应构造 helper。

提供普通 API 可复用的 HTTPException 构造工具。
不修改 FastAPI 默认 422 行为，不暴露内部信息。
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def business_error(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    """构造稳定的业务错误 HTTPException。

    detail 形状固定为 {"code": str, "message": str, "details": dict}。
    不包含 traceback、数据库路径、SQL、API key 或内部异常正文。
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": details if details is not None else {},
        },
    )
