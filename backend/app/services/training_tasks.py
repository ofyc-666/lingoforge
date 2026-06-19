"""训练任务薄封装服务。

基于 generated_tasks 表提供训练任务创建和归属校验。
不访问 Agent、LLM 或新增表。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.training import create_generated_task, get_generated_task


class TrainingTaskError(Exception):
    """训练任务业务错误基类。"""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class TrainingTaskNotFoundError(TrainingTaskError):
    """训练任务不存在。"""

    def __init__(self, task_id: int):
        super().__init__("TASK_NOT_FOUND", f"训练任务 {task_id} 不存在。", {"task_id": task_id})


class TrainingTaskAccessError(TrainingTaskError):
    """无权访问训练任务。"""

    def __init__(self, task_id: int):
        super().__init__("TASK_ACCESS_DENIED", f"无权访问训练任务 {task_id}。", {"task_id": task_id})


def create_task_from_analysis(
    database_path: str | Path,
    *,
    user_id: int,
    session_id: int,
    analysis: dict[str, Any],
) -> int:
    """将文本分析结果保存为 generated_tasks 记录。

    Args:
        database_path: 数据库路径。
        user_id: 任务所属用户 ID。
        session_id: 任务所属训练会话 ID。
        analysis: TextAnalysisResponse 序列化后的 dict。

    Returns:
        新生成的训练任务 ID。
    """
    keywords: list[dict[str, Any]] = analysis.get("keywords", [])
    target_ability = keywords[0]["ability"] if keywords else "VOCABULARY_CONTEXT"

    exercise = analysis.get("exercise") or {}
    questions: list[dict[str, Any]] = []
    if exercise:
        questions.append({
            "question_id": exercise.get("question_id", "q1"),
            "question_type": exercise.get("question_type", "MULTIPLE_CHOICE"),
            "prompt": exercise.get("prompt", ""),
            "options": exercise.get("options", []),
            "answer": exercise.get("answer", ""),
            "explanation": exercise.get("explanation", ""),
            "target_ability": exercise.get("target_ability", target_ability),
            "error_type_on_wrong": f"{target_ability}_ERROR",
        })

    content_json: dict[str, Any] = {
        "title": "词汇语境练习",
        "raw_text": analysis.get("raw_text", ""),
        "instructions": "请选择最符合语境的答案。",
        "questions": questions,
        "agent_feedback": analysis.get("agent_feedback", ""),
        "source": "TEXT_ANALYSIS_MOCK",
    }

    quality_check_result: dict[str, Any] = {
        "status": "PASSED",
        "source": "CONTRACT_MVP",
    }

    return create_generated_task(
        database_path,
        session_id=session_id,
        user_id=user_id,
        task_type="LOW_PRESSURE_LEARNING",
        target_ability=target_ability,
        content_json=content_json,
        quality_check_result=quality_check_result,
    )


def get_user_training_task(
    database_path: str | Path,
    *,
    user_id: int,
    task_id: int,
) -> dict[str, Any]:
    """按用户读取训练任务，非归属用户抛出受控错误。

    Args:
        database_path: 数据库路径。
        user_id: 请求用户 ID。
        task_id: 训练任务 ID。

    Returns:
        训练任务 dict（包含 JSON 字段反序列化结果）。

    Raises:
        TrainingTaskNotFoundError: 任务不存在。
        TrainingTaskAccessError: 任务不属于当前用户。
    """
    task = get_generated_task(database_path, task_id)
    if task is None:
        raise TrainingTaskNotFoundError(task_id)
    if task.get("user_id") != user_id:
        raise TrainingTaskAccessError(task_id)
    return task
