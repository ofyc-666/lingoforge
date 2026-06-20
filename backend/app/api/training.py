"""训练提交与结果查询 API 路由。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.training_models import TrainingSubmitRequest, TrainingSubmitResponse, TrainingResultResponse, TrainingTaskSummary
from app.config import Settings, load_settings
from app.constants import is_valid_workflow_stage
from app.repositories.training import (
    create_training_session,
    get_latest_training_submission_evidence,
    list_training_sessions_for_user,
)
from app.services.training_submission import TrainingSubmissionError, submit_training_task
from app.services.training_tasks import TrainingTaskAccessError, TrainingTaskNotFoundError, get_user_training_task

router = APIRouter(prefix="/api/training", tags=["training"])


# --------------- 会话模型 ---------------


class CreateSessionRequest(BaseModel):
    """创建训练会话请求体。身份来自请求头。"""

    model_config = ConfigDict(extra="forbid")

    stage: str = Field(..., min_length=1)

    @field_validator("stage")
    @classmethod
    def _validate_stage(cls, value: str) -> str:
        if not is_valid_workflow_stage(value):
            raise ValueError(f"stage 必须是合法的 WorkflowStage: {sorted(['DIAGNOSTIC','FIRST_MAIN','SIDEQUEST','SECOND_PLAN','SHORT_TRAINING','ISOLATED_TEST'])}")
        return value


class CreateSessionResponse(BaseModel):
    """创建训练会话响应体。"""

    session_id: int
    user_id: int
    stage: str
    status: str


class ListSessionsResponse(BaseModel):
    """训练会话列表响应体。"""

    sessions: list[dict[str, Any]]


def get_settings() -> Settings:
    return load_settings()


@router.post("/tasks/{task_id}/submit", response_model=TrainingSubmitResponse)
def submit_training(
    task_id: int,
    request: TrainingSubmitRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    settings: Settings = Depends(get_settings),
) -> TrainingSubmitResponse:
    """提交训练任务答案，执行评分→证据→画像建议闭环。"""
    try:
        result = submit_training_task(
            settings.database_path,
            user_id=user_id,
            task_id=task_id,
            answers=[a.model_dump() for a in request.answers],
            time_spent_seconds=request.time_spent_seconds,
            used_hints=request.used_hints,
        )
    except TrainingSubmissionError as exc:
        status_map = {
            "TASK_NOT_FOUND": 404,
            "TASK_ACCESS_DENIED": 403,
            "INVALID_TASK_CONTENT": 400,
        }
        status = status_map.get(exc.code, 500)
        raise HTTPException(
            status_code=status,
            detail={"code": exc.code, "message": exc.message, "details": exc.details},
        ) from exc

    return TrainingSubmitResponse(**result)


@router.get("/tasks/{task_id}/result", response_model=TrainingResultResponse)
def get_task_result(
    task_id: int,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    settings: Settings = Depends(get_settings),
) -> TrainingResultResponse:
    """查询训练任务结果，返回任务摘要和最新提交。"""
    try:
        task = get_user_training_task(settings.database_path, user_id=user_id, task_id=task_id)
    except TrainingTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message, "details": exc.details}) from exc
    except TrainingTaskAccessError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message, "details": exc.details}) from exc

    task_summary = TrainingTaskSummary(
        task_id=task["id"],
        session_id=task["session_id"],
        task_type=task["task_type"],
        target_ability=task["target_ability"],
        difficulty_params=task.get("difficulty_params", {}),
        content=task.get("content_json", {}),
        quality_check_result=task.get("quality_check_result", {}),
        created_at=task.get("created_at", ""),
    )

    # 查询最新提交
    latest_evidence = get_latest_training_submission_evidence(settings.database_path, task_id=task_id)
    latest_submission: dict[str, Any] | None = None
    if latest_evidence is not None:
        payload = latest_evidence.get("payload_json", {})
        score = payload.get("score", {})
        # 查找关联的画像建议
        from app.repositories.users import get_user_profile_suggestions
        suggestions = get_user_profile_suggestions(settings.database_path, user_id)
        profile_suggestion_id: int | None = None
        for s in suggestions:
            refs = s.get("evidence_refs", [])
            if latest_evidence["id"] in refs:
                profile_suggestion_id = s["id"]
                break

        latest_submission = {
            "evidence_id": latest_evidence["id"],
            "score": score,
            "question_results": payload.get("question_results", []),
            "profile_suggestion_id": profile_suggestion_id,
            "created_at": latest_evidence.get("created_at", ""),
        }

    return TrainingResultResponse(task=task_summary, latest_submission=latest_submission)


# --------------- 训练会话端点 ---------------


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(
    request: CreateSessionRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    settings: Settings = Depends(get_settings),
) -> CreateSessionResponse:
    """创建训练会话，状态为 IN_PROGRESS。"""
    session_id = create_training_session(
        settings.database_path,
        user_id=user_id,
        stage=request.stage,
        status="IN_PROGRESS",
    )
    return CreateSessionResponse(
        session_id=session_id,
        user_id=user_id,
        stage=request.stage,
        status="IN_PROGRESS",
    )


@router.get("/sessions", response_model=ListSessionsResponse)
def list_sessions(
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    settings: Settings = Depends(get_settings),
) -> ListSessionsResponse:
    """列出当前用户的训练会话，按 id DESC 排序，最多 20 条。"""
    sessions = list_training_sessions_for_user(settings.database_path, user_id)
    return ListSessionsResponse(sessions=sessions)
