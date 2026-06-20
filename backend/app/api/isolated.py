"""隔离测试 API 路由。

提供隔离测试开始和提交端点。
题目答案、解析、评分依据不进入 Agent Context。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.errors import business_error
from app.api.isolated_models import (
    IsolatedTestStartRequest,
    IsolatedTestStartResponse,
    IsolatedTestSubmitRequest,
    IsolatedTestSubmitResponse,
)
from app.config import Settings, load_settings
from app.services.isolated_tests import start_isolated_test, submit_isolated_test

router = APIRouter(prefix="/api/isolated-tests", tags=["isolated-tests"])


def get_settings() -> Settings:
    return load_settings()


@router.post("/start", response_model=IsolatedTestStartResponse)
def start_test(
    request: IsolatedTestStartRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    session_id: int | None = Header(None, alias="X-LingoForge-Session-Id"),
    settings: Settings = Depends(get_settings),
) -> IsolatedTestStartResponse:
    """开始一次隔离测试，从 active items 中按 target_ability 选择题目。

    返回 sanitized items，不含答案、解析或评分依据。
    """
    try:
        result = start_isolated_test(
            settings.database_path,
            user_id=user_id,
            target_ability=request.target_ability,
            limit=request.limit,
            session_id=session_id,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("NO_ACTIVE_ITEMS:"):
            ability = msg.split(":", 1)[1]
            raise business_error(
                400, "NO_ACTIVE_ITEMS",
                f"没有可用的 {ability} 隔离测试题。",
                {"target_ability": ability},
            ) from exc
        if msg == "SESSION_NOT_FOUND":
            raise business_error(
                404, "SESSION_NOT_FOUND",
                f"训练会话 {session_id} 不存在。",
                {"session_id": session_id},
            ) from exc
        if msg == "SESSION_ACCESS_DENIED":
            raise business_error(
                403, "SESSION_ACCESS_DENIED",
                f"无权使用训练会话 {session_id}。",
                {"session_id": session_id},
            ) from exc
        raise

    return IsolatedTestStartResponse(
        attempt_id=result["attempt_id"],
        items=result["items"],
    )


@router.post("/attempts/{attempt_id}/submit", response_model=dict[str, Any])
def submit_test(
    attempt_id: int,
    request: IsolatedTestSubmitRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """提交隔离测试答案。

    执行确定性评分并返回受控结果包。
    不返回完整答案、详细解析、干扰项设计或隔离题全文。
    """
    try:
        result = submit_isolated_test(
            settings.database_path,
            user_id=user_id,
            attempt_id=attempt_id,
            answers=request.answers,
            time_spent_seconds=request.time_spent_seconds,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg == "ATTEMPT_NOT_FOUND":
            raise business_error(
                404, "ATTEMPT_NOT_FOUND",
                f"隔离测试尝试 {attempt_id} 不存在。",
                {"attempt_id": attempt_id},
            ) from exc
        if msg == "ATTEMPT_ACCESS_DENIED":
            raise business_error(
                403, "ATTEMPT_ACCESS_DENIED",
                f"无权访问隔离测试尝试 {attempt_id}。",
                {"attempt_id": attempt_id},
            ) from exc
        if msg == "ATTEMPT_ALREADY_SUBMITTED":
            raise business_error(
                409, "ATTEMPT_ALREADY_SUBMITTED",
                f"隔离测试尝试 {attempt_id} 已提交，不可重复提交。",
                {"attempt_id": attempt_id},
            ) from exc
        raise

    return result
