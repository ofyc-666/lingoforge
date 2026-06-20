"""每日计划、背词和刷题 API 模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

# 禁止请求体中出现身份字段
FORBIDDEN_IDENTITY_FIELDS = frozenset({
    "user_id", "session_id", "current_user_id", "current_session_id", "permission_scope",
})


def _reject_identity_fields(data: dict[str, Any]) -> None:
    """如果请求体包含身份字段，直接拒绝（422）。"""
    forbidden = [k for k in FORBIDDEN_IDENTITY_FIELDS if k in data]
    if forbidden:
        raise ValueError(f"IDENTITY_IN_BODY:{','.join(forbidden)}")


# ---- 生成每日计划 ----


class GenerateDailyPlanRequest(BaseModel):
    regenerate: bool = False
    preferred_practice_mode: str | None = Field(default=None, pattern=r"^(TARGETED_PRACTICE|COMPREHENSIVE_SIMULATION)$")
    max_new_words: int = Field(default=8, ge=1, le=20)
    max_review_words: int = Field(default=12, ge=1, le=30)

    @model_validator(mode="before")
    @classmethod
    def reject_identity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            _reject_identity_fields(data)
        return data


# ---- 背词事件 ----


class ReviewEventItem(BaseModel):
    vocabulary_item_id: int
    event_type: str = Field(pattern=r"^(WORD_SHOWN|SELF_RATING|MEANING_CHECK|CONTEXT_CHECK|WORD_IN_SENTENCE|REVIEW_COMPLETED)$")
    answer: dict[str, Any] | None = None
    is_correct: bool | None = None
    self_rating: str | None = Field(default=None, pattern=r"^(KNOWN|FUZZY|UNKNOWN)$")
    used_hint: bool = False
    time_spent_seconds: int | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_identity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            _reject_identity_fields(data)
        return data


class CreateReviewEventsRequest(BaseModel):
    plan_id: int
    events: list[ReviewEventItem]

    @model_validator(mode="before")
    @classmethod
    def reject_identity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            _reject_identity_fields(data)
        return data


# ---- 刷题练习 ----


class StartPracticeRequest(BaseModel):
    practice_mode: str = Field(default="TARGETED_PRACTICE", pattern=r"^(TARGETED_PRACTICE|COMPREHENSIVE_SIMULATION)$")
    target_abilities: list[str] | None = None
    max_questions: int = Field(default=5, ge=2, le=15)

    @model_validator(mode="before")
    @classmethod
    def reject_identity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            _reject_identity_fields(data)
        return data


class PracticeResponse(BaseModel):
    plan_id: int
    practice_mode: str
    task_id: int | None = None
    session_id: int | None = None
    target_abilities: list[str] = []
    selected_skills: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    message: str = ""


class DailyPlanResponse(BaseModel):
    plan_id: int
    user_id: int
    plan_date: str
    status: str
    practice_mode: str
    target_abilities: list[str]
    selected_skills: list[dict[str, Any]]
    difficulty_params: dict[str, Any]
    hint_strategy: dict[str, Any]
    rationale: str
    estimated_minutes: int | None
    candidate_event_id: int | None
    vocabulary_items: list[dict[str, Any]]
    created_at: str

    @classmethod
    def from_plan(cls, plan: dict[str, Any], vocab_items: list[dict[str, Any]]) -> "DailyPlanResponse":
        return cls(
            plan_id=plan["id"],
            user_id=plan["user_id"],
            plan_date=plan["plan_date"],
            status=plan["status"],
            practice_mode=plan["practice_mode"],
            target_abilities=plan["target_abilities"],
            selected_skills=plan["selected_skills"],
            difficulty_params=plan["difficulty_params"],
            hint_strategy=plan["hint_strategy"],
            rationale=plan["rationale"],
            estimated_minutes=plan["estimated_minutes"],
            candidate_event_id=plan["candidate_event_id"],
            vocabulary_items=vocab_items,
            created_at=plan["created_at"],
        )
