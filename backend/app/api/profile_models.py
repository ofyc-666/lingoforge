"""用户画像相关 Pydantic 模型。

Pydantic v2 模型，身份字段不在请求体中。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProfileGoalRequest(BaseModel):
    """用户目标保存请求体。

    身份来自请求头，请求体禁止出现 user_id/session_id/permission_scope。
    """

    model_config = ConfigDict(extra="forbid")

    exam_type: str = Field(default="CET-6", min_length=1)
    days_until_exam: int | None = Field(default=None, ge=0)
    target_score: int | None = Field(default=None, ge=0)
    daily_minutes: int | None = Field(default=None, ge=0)
    self_reported_weaknesses: list[str] = Field(default_factory=list)
    interest_topics: list[str] = Field(default_factory=list)


class ProfileGoalResponse(BaseModel):
    """用户目标保存响应体。"""

    goal_id: int
    user_id: int


class ProfileSummaryResponse(BaseModel):
    """用户画像摘要响应体。"""

    user: dict[str, Any]
    latest_goal: dict[str, Any]
    latest_profile: dict[str, Any]
    pending_suggestions: list[dict[str, Any]]
