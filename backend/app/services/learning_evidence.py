"""学习证据写入服务。

封装训练提交证据的 append-only 写入。
不调用 Agent/LLM，不做画像更新。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.training import create_learning_evidence


def build_training_submission_evidence_payload(
    *,
    session_id: int,
    task_id: int,
    answers: list[dict[str, Any]],
    score_result: dict[str, Any],
    time_spent_seconds: int | None = None,
    used_hints: list[str] | None = None,
) -> dict[str, Any]:
    """构造 TRAINING_ANSWER 原始证据 payload，不执行数据库写入。"""
    payload: dict[str, Any] = {
        "event": "TRAINING_SUBMISSION_SCORED",
        "task_id": task_id,
        "session_id": session_id,
        "answers": answers,
        "score": {
            "total": score_result.get("total"),
            "correct": score_result.get("correct"),
            "accuracy": score_result.get("accuracy"),
            "passed": score_result.get("passed"),
        },
        "question_results": score_result.get("question_results", []),
        "target_abilities": [],
        "error_types": score_result.get("error_types", []),
        "used_hints": list(used_hints or []),
        "time_spent_seconds": time_spent_seconds,
    }

    seen_abilities: set[str] = set()
    for qr in score_result.get("question_results", []):
        ability = qr.get("target_ability")
        if ability and ability not in seen_abilities:
            seen_abilities.add(ability)
            payload["target_abilities"].append(ability)

    return payload


def record_training_submission_evidence(
    database_path: str | Path,
    *,
    user_id: int,
    session_id: int,
    task_id: int,
    answers: list[dict[str, Any]],
    score_result: dict[str, Any],
    time_spent_seconds: int | None = None,
    used_hints: list[str] | None = None,
) -> int:
    """写入一条 TRAINING_ANSWER 学习证据，返回新 evidence ID。

    原始学习证据只追加，不覆盖旧记录。

    Args:
        database_path: 数据库路径。
        user_id: 提交用户 ID。
        session_id: 训练会话 ID。
        task_id: 训练任务 ID。
        answers: 用户提交答案列表。
        score_result: 评分器输出。
        time_spent_seconds: 提交耗时（可选）。
        used_hints: 使用的提示列表（可选）。

    Returns:
        新写入的学习证据 ID。
    """
    payload: dict[str, Any] = {
        "event": "TRAINING_SUBMISSION_SCORED",
        "task_id": task_id,
        "session_id": session_id,
        "answers": answers,
        "score": {
            "total": score_result.get("total"),
            "correct": score_result.get("correct"),
            "accuracy": score_result.get("accuracy"),
            "passed": score_result.get("passed"),
        },
        "question_results": score_result.get("question_results", []),
        "target_abilities": [],
        "error_types": score_result.get("error_types", []),
        "used_hints": list(used_hints or []),
        "time_spent_seconds": time_spent_seconds,
    }

    # 从评分结果中提取 target_abilities
    seen_abilities: set[str] = set()
    for qr in score_result.get("question_results", []):
        ability = qr.get("target_ability")
        if ability and ability not in seen_abilities:
            seen_abilities.add(ability)
            payload["target_abilities"].append(ability)

    return create_learning_evidence(
        database_path,
        user_id=user_id,
        session_id=session_id,
        task_id=task_id,
        evidence_type="TRAINING_ANSWER",
        payload=payload,
    )
