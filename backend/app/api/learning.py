"""文本分析 API 路由。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.learning_models import TextAnalysisRequest, TextAnalysisResponse
from app.config import Settings, load_settings
from app.repositories.base import fetch_one
from app.services.learning_analysis import analyze_english_text
from app.services.task_validation import record_task_validation_result, validate_training_task_content
from app.services.training_tasks import create_task_from_analysis

router = APIRouter(prefix="/api/learning", tags=["learning"])


def get_settings() -> Settings:
    return load_settings()


@router.post("/analyze-text", response_model=TextAnalysisResponse)
def analyze_text(
    request: TextAnalysisRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    session_id: int | None = Header(None, alias="X-LingoForge-Session-Id"),
) -> TextAnalysisResponse:
    """对英文文本进行确定性分析，返回关键词、练习题和反馈。"""
    return analyze_english_text(request)


@router.post("/analyze-text/create-task", response_model=dict[str, Any])
def analyze_text_and_create_task(
    request: TextAnalysisRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    session_id: int = Header(..., alias="X-LingoForge-Session-Id"),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """对文本进行确定性分析并创建训练任务。

    先执行现有确定性文本分析，再写入 generated_tasks，
    然后调用质量校验服务并写入 validation。
    """
    # 校验 session 归属
    session = fetch_one(
        settings.database_path,
        "SELECT * FROM training_sessions WHERE id = ?",
        (session_id,),
    )
    if session is None:
        raise HTTPException(status_code=404, detail={
            "code": "SESSION_NOT_FOUND",
            "message": f"训练会话 {session_id} 不存在。",
            "details": {"session_id": session_id},
        })
    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail={
            "code": "SESSION_ACCESS_DENIED",
            "message": f"无权使用训练会话 {session_id}。",
            "details": {"session_id": session_id},
        })

    # 执行确定性文本分析
    analysis_response = analyze_english_text(request)
    analysis_dict = analysis_response.model_dump()

    # 创建训练任务
    task_id = create_task_from_analysis(
        settings.database_path,
        user_id=user_id,
        session_id=session_id,
        analysis=analysis_dict,
    )

    # 质量校验
    from app.repositories.training import get_generated_task
    task = get_generated_task(settings.database_path, task_id)
    if task and task.get("content_json"):
        validation_result = validate_training_task_content(task["content_json"])
        record_task_validation_result(
            settings.database_path,
            task_id=task_id,
            validation_result=validation_result,
        )

    return {
        "analysis": analysis_dict,
        "task_id": task_id,
    }
