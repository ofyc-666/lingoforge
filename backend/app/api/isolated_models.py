"""隔离测试请求与响应 Pydantic 模型。

所有模型禁止身份字段（user_id/session_id/permission_scope）。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IsolatedTestStartRequest(BaseModel):
    """隔离测试开始请求体。"""

    model_config = ConfigDict(extra="forbid")

    target_ability: str = Field(..., min_length=1, description="目标能力维度")
    limit: int = Field(default=3, ge=1, le=20, description="最多返回的题目数")


class IsolatedTestItem(BaseModel):
    """隔离测试题项（sanitized，不含答案）。"""

    item_id: int
    item_order: int
    target_ability: str
    item_version: str
    prompt: str
    options: list[dict[str, str]]


class IsolatedTestStartResponse(BaseModel):
    """隔离测试开始响应体。"""

    attempt_id: int
    items: list[dict[str, Any]]


class IsolatedTestAnswer(BaseModel):
    """用户提交的单个隔离测试答案。"""

    model_config = ConfigDict(extra="forbid")

    item_id: int
    answer: str = Field(..., min_length=1)


class IsolatedTestSubmitRequest(BaseModel):
    """隔离测试提交请求体。"""

    model_config = ConfigDict(extra="forbid")

    answers: list[dict[str, Any]] = Field(..., min_length=1)
    time_spent_seconds: int | None = Field(default=None, ge=0)


class IsolatedTestScore(BaseModel):
    """隔离测试评分。"""

    total: int
    correct: int
    accuracy: float


class IsolatedItemResult(BaseModel):
    """单题结果（受控，不包含完整答案）。"""

    item_id: int
    target_ability: str
    is_correct: bool


class IsolatedTestSubmitResponse(BaseModel):
    """隔离测试提交响应体（受控结果包）。"""

    attempt_id: int
    score: dict[str, Any]
    item_results: list[dict[str, Any]]
    evidence_id: int
    safe_explanation: str
