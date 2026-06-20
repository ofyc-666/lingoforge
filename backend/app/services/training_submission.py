"""训练提交编排服务。

组合任务归属校验、评分、证据写入和画像建议写入，
形成训练提交完整业务闭环。
不调用 Agent/LLM，不新增表。
"""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
from typing import Any

from app.database import connect
from app.services.learning_evidence import build_training_submission_evidence_payload
from app.services.profile_suggestions import build_profile_suggestion_from_score
from app.services.training_scorer import UnsupportedQuestionTypeError, score_training_submission
from app.storage.json_fields import to_json_text
from app.services.training_tasks import (
    TrainingTaskAccessError,
    TrainingTaskNotFoundError,
    get_user_training_task,
)


class TrainingSubmissionError(Exception):
    """训练提交业务错误。"""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _write_submission_artifacts_atomically(
    database_path: str | Path,
    *,
    user_id: int,
    session_id: int,
    task_id: int,
    answers: list[dict[str, Any]],
    score_result: dict[str, Any],
    time_spent_seconds: int | None,
    used_hints: list[str] | None,
) -> tuple[int, int]:
    """同一事务写入学习证据和画像建议，避免部分写入。"""
    evidence_payload = build_training_submission_evidence_payload(
        session_id=session_id,
        task_id=task_id,
        answers=answers,
        score_result=score_result,
        time_spent_seconds=time_spent_seconds,
        used_hints=used_hints,
    )

    with closing(connect(database_path)) as conn:
        try:
            evidence_cursor = conn.execute(
                """INSERT INTO learning_evidence
                   (user_id, session_id, task_id, evidence_type, payload_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    session_id,
                    task_id,
                    "TRAINING_ANSWER",
                    to_json_text(evidence_payload),
                ),
            )
            evidence_id = int(evidence_cursor.lastrowid)

            suggestion = build_profile_suggestion_from_score(
                evidence_id=evidence_id,
                score_result=score_result,
            )
            suggestion_cursor = conn.execute(
                """INSERT INTO profile_update_suggestions
                   (user_id, ability, direction, reason, evidence_refs, agent_payload)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    suggestion["ability"],
                    suggestion["direction"],
                    suggestion["reason"],
                    to_json_text(suggestion["evidence_refs"]),
                    to_json_text(suggestion["agent_payload"]),
                ),
            )
            profile_suggestion_id = int(suggestion_cursor.lastrowid)
            conn.commit()
            return evidence_id, profile_suggestion_id
        except Exception:
            conn.rollback()
            raise


def submit_training_task(
    database_path: str | Path,
    *,
    user_id: int,
    task_id: int,
    answers: list[dict[str, Any]],
    time_spent_seconds: int | None = None,
    used_hints: list[str] | None = None,
) -> dict[str, Any]:
    """提交训练任务，执行完整评分→证据→画像建议闭环。

    Args:
        database_path: 数据库路径。
        user_id: 提交用户 ID。
        task_id: 训练任务 ID。
        answers: 用户答案列表 [{question_id, answer}, ...]。
        time_spent_seconds: 提交耗时。
        used_hints: 使用的提示列表。

    Returns:
        训练提交响应 dict:
        {
            task_id, session_id, score, question_results,
            evidence_id, profile_suggestion_id, agent_feedback
        }

    Raises:
        TrainingSubmissionError: 任务不存在、无权访问或内容不合法。
    """
    # 1. 归属校验
    try:
        task = get_user_training_task(database_path, user_id=user_id, task_id=task_id)
    except (TrainingTaskNotFoundError, TrainingTaskAccessError) as exc:
        raise TrainingSubmissionError(exc.code, exc.message, exc.details) from exc

    session_id = int(task.get("session_id", 0))

    # 2. 获取任务内容并校验
    content: dict[str, Any] = task.get("content_json", {})
    questions: list[dict[str, Any]] = content.get("questions", [])
    if not questions:
        raise TrainingSubmissionError(
            "INVALID_TASK_CONTENT",
            f"训练任务 {task_id} 不含有效题目。",
            {"task_id": task_id},
        )

    # 3. 确定题分
    try:
        score_result = score_training_submission(
            {"questions": questions},
            answers,
            used_hints=used_hints,
        )
    except UnsupportedQuestionTypeError as exc:
        raise TrainingSubmissionError(
            "INVALID_TASK_CONTENT",
            f"训练任务 {task_id} 包含 MVP 不支持的题型。",
            {
                "task_id": task_id,
                "question_id": exc.question_id,
                "question_type": exc.question_type,
            },
        ) from exc

    # 4. 写入学习证据
    evidence_id, profile_suggestion_id = _write_submission_artifacts_atomically(
        database_path,
        user_id=user_id,
        session_id=session_id,
        task_id=task_id,
        answers=answers,
        score_result=score_result,
        time_spent_seconds=time_spent_seconds,
        used_hints=used_hints,
    )

    # 5. 生成 agent_feedback（确定性模板）
    accuracy = score_result.get("accuracy", 0.0)
    if accuracy >= 1.0:
        agent_feedback = "全部正确！继续保持，可以尝试更高难度的练习。"
    elif accuracy >= 0.6:
        agent_feedback = "完成得不错，建议回顾错题解析，重点理解错误选项的排除理由。"
    else:
        agent_feedback = "本次正确率偏低，建议先巩固词汇基础，再回到语境中判断词义。"

    return {
        "task_id": task_id,
        "session_id": session_id,
        "score": {
            "total": score_result["total"],
            "correct": score_result["correct"],
            "accuracy": score_result["accuracy"],
            "passed": score_result["passed"],
        },
        "question_results": score_result["question_results"],
        "evidence_id": evidence_id,
        "profile_suggestion_id": profile_suggestion_id,
        "agent_feedback": agent_feedback,
    }
