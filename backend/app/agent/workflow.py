"""MVP Agent Workflow 薄编排。

本模块只负责把 AgentRun 与现有确定性业务服务接起来：
文本分析 -> 训练任务 -> 质量校验 -> 近期记忆提议。
评分、证据和画像建议继续由 training_submission 服务负责。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agent.memory import write_memory_item
from app.agent.models import RuntimeContext
from app.agent.runtime import AgentRuntime
from app.api.learning_models import TextAnalysisRequest
from app.llm.provider import LLMProvider
from app.repositories.base import fetch_one
from app.repositories.training import get_generated_task
from app.services.learning_analysis import analyze_english_text
from app.services.task_validation import record_task_validation_result, validate_training_task_content
from app.services.training_tasks import create_task_from_analysis


class AgentWorkflowError(Exception):
    """Agent Workflow 受控错误。"""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def run_text_training_workflow(
    database_path: str | Path,
    *,
    provider: LLMProvider,
    user_id: int,
    session_id: int,
    raw_text: str,
    target_abilities: list[str] | None = None,
    max_keywords: int = 5,
    generate_exercise: bool = True,
) -> dict[str, Any]:
    """运行 MVP 主线：Agent 决策 + 确定性文本分析 + 训练任务生成。"""

    _ensure_session_belongs_to_user(database_path, user_id=user_id, session_id=session_id)

    context = RuntimeContext(
        user_id=user_id,
        session_id=session_id,
        workflow_stage="FIRST_MAIN",
        objective="分析英文材料并生成一次 CET-6 词汇语境训练",
        allowed_tools=("get_user_profile", "analyze_learning_history"),
        permission_scope=("read_user_profile", "read_learning_history"),
    )
    agent_result = AgentRuntime(database_path=database_path, provider=provider).run(context)

    if agent_result.status == "FAILED_VALIDATION":
        raise AgentWorkflowError(
            "AGENT_DECISION_INVALID",
            "Agent 决策未通过结构化校验。",
            {"validation": agent_result.validation},
        )

    analysis_response = analyze_english_text(TextAnalysisRequest(
        raw_text=raw_text,
        target_abilities=target_abilities or ["VOCABULARY_CONTEXT"],
        max_keywords=max_keywords,
        generate_exercise=generate_exercise,
    ))
    analysis = analysis_response.model_dump()

    task_id = create_task_from_analysis(
        database_path,
        user_id=user_id,
        session_id=session_id,
        analysis=analysis,
    )
    task = get_generated_task(database_path, task_id)
    validation_result = validate_training_task_content(task["content_json"] if task else {})
    validation_id = record_task_validation_result(
        database_path,
        task_id=task_id,
        validation_result=validation_result,
    )
    if validation_result.get("status") != "PASSED":
        raise AgentWorkflowError(
            "TRAINING_TASK_VALIDATION_FAILED",
            "生成训练任务未通过确定性质量校验。",
            {"task_id": task_id, "validation": validation_result},
        )

    memory_id = write_memory_item(
        database_path,
        user_id=user_id,
        session_id=session_id,
        memory_type="RECENT_TRAINING_PLAN",
        content={
            "workflow_stage": "FIRST_MAIN",
            "analysis_id": analysis["analysis_id"],
            "task_id": task_id,
            "target_abilities": target_abilities or ["VOCABULARY_CONTEXT"],
            "summary": "本轮根据英文材料生成了词汇语境训练任务。",
        },
        source_refs=[
            {"type": "generated_task", "id": task_id},
            {"type": "agent_decision_log", "id": agent_result.agent_decision_log_id},
        ],
        status="ACTIVE",
    )

    return {
        "agent_run": agent_result,
        "analysis": analysis,
        "task_id": task_id,
        "task": task,
        "validation": {
            "validation_id": validation_id,
            **validation_result,
        },
        "memory_id": memory_id,
        "workflow_status": "READY_FOR_SUBMISSION",
    }


def _ensure_session_belongs_to_user(
    database_path: str | Path,
    *,
    user_id: int,
    session_id: int,
) -> None:
    session = fetch_one(
        database_path,
        "SELECT * FROM training_sessions WHERE id = ?",
        (session_id,),
    )
    if session is None:
        raise AgentWorkflowError(
            "SESSION_NOT_FOUND",
            f"训练会话 {session_id} 不存在。",
            {"session_id": session_id},
        )
    if session.get("user_id") != user_id:
        raise AgentWorkflowError(
            "SESSION_ACCESS_DENIED",
            f"无权使用训练会话 {session_id}。",
            {"session_id": session_id},
        )
