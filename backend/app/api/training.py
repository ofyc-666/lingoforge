"""训练提交与结果查询 API 路由。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.training_models import TrainingSubmitRequest, TrainingSubmitResponse, TrainingResultResponse, TrainingTaskSummary
from app.config import Settings, load_settings
from app.repositories.training import get_learning_evidence_by_task
from app.services.training_submission import TrainingSubmissionError, submit_training_task
from app.services.training_tasks import TrainingTaskAccessError, TrainingTaskNotFoundError, get_user_training_task

router = APIRouter(prefix="/api/training", tags=["training"])


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
    evidence_list = get_learning_evidence_by_task(settings.database_path, task_id)
    latest_submission: dict[str, Any] | None = None
    if evidence_list:
        latest_evidence = evidence_list[-1]
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
