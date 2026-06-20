"""用户画像 API 路由。

提供用户画像摘要和目标保存端点。
身份只能从请求头绑定，不从请求体读取。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.errors import business_error
from app.api.profile_models import ProfileGoalRequest, ProfileGoalResponse, ProfileSummaryResponse
from app.config import Settings, load_settings
from app.repositories.users import (
    create_user,
    get_latest_profile,
    get_latest_user_goal,
    get_user,
    get_user_profile_suggestions,
    save_user_goal,
)

router = APIRouter(prefix="/api/profile", tags=["profile"])


def get_settings() -> Settings:
    return load_settings()


@router.get("/summary", response_model=ProfileSummaryResponse)
def get_profile_summary(
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    settings: Settings = Depends(get_settings),
) -> ProfileSummaryResponse:
    """获取当前用户画像摘要。

    返回用户基本信息、最新目标、最新画像快照和待处理画像建议。
    只从请求头绑定 user_id，不信任请求体中的身份信息。
    """
    user = get_user(settings.database_path, user_id)
    if user is None:
        raise business_error(404, "USER_NOT_FOUND", f"用户 {user_id} 不存在。", {"user_id": user_id})

    latest_goal = get_latest_user_goal(settings.database_path, user_id)
    latest_profile = get_latest_profile(settings.database_path, user_id)
    all_suggestions = get_user_profile_suggestions(settings.database_path, user_id)
    pending_suggestions = [s for s in all_suggestions if s.get("validation_status") == "NEEDS_REVIEW"]

    return ProfileSummaryResponse(
        user={
            "id": user["id"],
            "display_name": user["display_name"],
        },
        latest_goal=latest_goal or {},
        latest_profile=latest_profile or {},
        pending_suggestions=pending_suggestions,
    )


@router.post("/goal", response_model=ProfileGoalResponse)
def create_profile_goal(
    request: ProfileGoalRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    settings: Settings = Depends(get_settings),
) -> ProfileGoalResponse:
    """保存用户学习目标。"""
    # 检查用户是否存在
    user = get_user(settings.database_path, user_id)
    if user is None:
        raise business_error(404, "USER_NOT_FOUND", f"用户 {user_id} 不存在。", {"user_id": user_id})

    goal_id = save_user_goal(
        settings.database_path,
        user_id=user_id,
        exam_type=request.exam_type,
        days_until_exam=request.days_until_exam,
        target_score=request.target_score,
        daily_minutes=request.daily_minutes,
        self_reported_weaknesses=request.self_reported_weaknesses,
        interest_topics=request.interest_topics,
    )

    return ProfileGoalResponse(goal_id=goal_id, user_id=user_id)
