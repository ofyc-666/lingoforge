"""每日计划、背词与刷题 API。"""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request

from app.api.daily_plan_models import (
    CreateReviewEventsRequest,
    DailyPlanResponse,
    GenerateDailyPlanRequest,
    PracticeResponse,
    StartPracticeRequest,
)
from app.config import Settings, load_settings
from app.llm.factory import create_llm_provider
from app.services.daily_plan import generate_daily_plan
from app.services.practice_gen import start_practice
from app.services.vocab_review import complete_vocabulary_phase, process_review_events

router = APIRouter(prefix="/api", tags=["daily-plan"])


def get_settings() -> Settings:
    return load_settings()


def _get_user_id(x_user_id: str = Header(..., alias="X-LingoForge-User-Id")) -> int:
    try:
        return int(x_user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail={"code": "INVALID_USER_ID", "message": "X-LingoForge-User-Id 必须是整数"})


def _get_session_id(
    x_session_id: str | None = Header(default=None, alias="X-LingoForge-Session-Id"),
) -> int | None:
    if x_session_id is None:
        return None
    try:
        return int(x_session_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail={"code": "INVALID_SESSION_ID", "message": "X-LingoForge-Session-Id 必须是整数"})


# ---- 每日计划 ----


@router.post("/daily-plans/generate")
def api_generate_daily_plan(
    body: GenerateDailyPlanRequest,
    user_id: int = Depends(_get_user_id),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """生成或返回今天的每日学习计划。"""
    try:
        provider = create_llm_provider(settings)
        result = generate_daily_plan(
            settings.database_path,
            provider=provider,
            user_id=user_id,
            regenerate=body.regenerate,
            preferred_practice_mode=body.preferred_practice_mode,
            max_new_words=body.max_new_words,
            max_review_words=body.max_review_words,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "PLAN_GENERATION_FAILED", "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(e)})


@router.get("/daily-plans/today")
def api_get_today_plan(
    user_id: int = Depends(_get_user_id),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """获取当前用户今日计划。"""
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    from app.repositories.daily_plan import get_today_plan, get_plan_vocabulary_items
    plan = get_today_plan(settings.database_path, user_id, today)
    if plan is None:
        raise HTTPException(status_code=404, detail={"code": "NO_PLAN_TODAY", "message": "今天还没有学习计划，请先生成。"})
    vocab = get_plan_vocabulary_items(settings.database_path, plan["id"])
    return DailyPlanResponse.from_plan(plan, vocab).model_dump()


# ---- 背词事件 ----


@router.post("/vocabulary/review-events")
def api_create_review_events(
    body: CreateReviewEventsRequest,
    user_id: int = Depends(_get_user_id),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """记录背词事件并返回最新词汇状态。"""
    try:
        events = [e.model_dump() for e in body.events]
        result = process_review_events(
            settings.database_path,
            user_id=user_id,
            plan_id=body.plan_id,
            events=events,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "REVIEW_EVENT_FAILED", "message": str(e)})


@router.post("/daily-plans/{plan_id}/vocabulary/complete")
def api_complete_vocabulary(
    plan_id: int,
    user_id: int = Depends(_get_user_id),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """完成今日背词阶段。"""
    try:
        result = complete_vocabulary_phase(settings.database_path, plan_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "COMPLETE_FAILED", "message": str(e)})


# ---- 刷题 ----


@router.post("/daily-plans/{plan_id}/practice/start")
def api_start_practice(
    plan_id: int,
    body: StartPracticeRequest,
    user_id: int = Depends(_get_user_id),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """按计划生成针对性训练或综合模拟题。"""
    try:
        result = start_practice(
            settings.database_path,
            user_id=user_id,
            plan_id=plan_id,
            practice_mode=body.practice_mode,
            target_abilities=body.target_abilities,
            max_questions=body.max_questions,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "PRACTICE_START_FAILED", "message": str(e)})
