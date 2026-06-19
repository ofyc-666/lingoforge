"""训练任务、提交与结果模型。

Pydantic v2 模型，字段与 docs/IMPLEMENTATION_CONTRACTS.md 第 3、4、5 节一致。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TrainingOption(BaseModel):
    """训练题选项。"""

    id: str = Field(..., min_length=1, description="选项标识，如 A/B/C/D")
    text: str = Field(..., min_length=1, description="选项文本")


class TrainingQuestion(BaseModel):
    """训练题目（MVP 仅 MULTIPLE_CHOICE）。"""

    question_id: str = Field(..., min_length=1)
    question_type: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    options: list[TrainingOption] = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    explanation: str = Field(default="")
    target_ability: str = Field(..., min_length=1)
    error_type_on_wrong: str | None = Field(default=None)


class TrainingTaskContent(BaseModel):
    """训练任务正文，写入 generated_tasks.content_json。"""

    title: str = Field(..., min_length=1)
    raw_text: str = Field(default="")
    instructions: str = Field(..., min_length=1)
    questions: list[TrainingQuestion] = Field(..., min_length=1)
    agent_feedback: str = Field(default="")
    source: str = Field(default="")


class TrainingAnswer(BaseModel):
    """用户提交的单个答案。"""

    question_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class TrainingSubmitRequest(BaseModel):
    """训练提交请求体。"""

    model_config = ConfigDict(extra="forbid")

    answers: list[TrainingAnswer] = Field(..., min_length=1)
    time_spent_seconds: int | None = Field(default=None, ge=0)
    used_hints: list[str] | None = Field(default=None)


class QuestionScoreResult(BaseModel):
    """单题评分结果。"""

    question_id: str = Field(..., min_length=1)
    user_answer: str = Field(default="")
    standard_answer: str = Field(..., min_length=1)
    is_correct: bool
    error_type: str | None = Field(default=None)
    target_ability: str = Field(..., min_length=1)
    explanation: str = Field(default="")


class TrainingScore(BaseModel):
    """训练任务总体评分。"""

    total: int = Field(..., ge=0)
    correct: int = Field(..., ge=0)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    passed: bool


class TrainingSubmitResponse(BaseModel):
    """训练提交响应体。"""

    task_id: int
    session_id: int
    score: TrainingScore
    question_results: list[QuestionScoreResult]
    evidence_id: int
    profile_suggestion_id: int | None = None
    agent_feedback: str = ""


class TrainingTaskSummary(BaseModel):
    """训练任务摘要。"""

    task_id: int
    session_id: int
    task_type: str
    target_ability: str
    difficulty_params: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    quality_check_result: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class TrainingResultResponse(BaseModel):
    """训练结果查询响应体。"""

    task: TrainingTaskSummary
    latest_submission: dict[str, Any] | None = None
