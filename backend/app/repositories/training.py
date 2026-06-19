"""训练会话、生成任务和学习证据 Repository。

为 training_sessions、generated_tasks、generated_task_validations、
learning_evidence 提供普通 CRUD 和按用户/会话查询。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all, fetch_one
from app.storage.json_fields import from_json_text, to_json_text


# --------------- 训练会话 ---------------

def create_training_session(
    database_path: str | Path,
    user_id: int,
    stage: str,
    status: str = "PENDING",
) -> int:
    """创建训练会话，返回新记录 ID。"""
    return execute(
        database_path,
        "INSERT INTO training_sessions (user_id, stage, status) VALUES (?, ?, ?)",
        (user_id, stage, status),
    )


def update_session_status(
    database_path: str | Path,
    session_id: int,
    status: str,
) -> None:
    """更新训练会话状态并写入完成时间。"""
    if status == "COMPLETED":
        execute(
            database_path,
            "UPDATE training_sessions SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, session_id),
        )
    else:
        execute(
            database_path,
            "UPDATE training_sessions SET status = ? WHERE id = ?",
            (status, session_id),
        )


# --------------- 生成任务 ---------------

def create_generated_task(
    database_path: str | Path,
    session_id: int,
    user_id: int,
    task_type: str,
    target_ability: str,
    skill_version_id: int | None = None,
    difficulty_params: dict[str, Any] | None = None,
    content_json: dict[str, Any] | None = None,
    quality_requirements: dict[str, Any] | None = None,
    quality_check_result: dict[str, Any] | None = None,
) -> int:
    """创建生成任务，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO generated_tasks
           (session_id, user_id, task_type, skill_version_id, target_ability,
            difficulty_params, content_json, quality_requirements, quality_check_result)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            user_id,
            task_type,
            skill_version_id,
            target_ability,
            to_json_text(difficulty_params or {}),
            to_json_text(content_json or {}),
            to_json_text(quality_requirements or {}),
            to_json_text(quality_check_result or {}),
        ),
    )


def get_generated_task(database_path: str | Path, task_id: int) -> dict[str, Any] | None:
    """获取生成任务。"""
    row = fetch_one(database_path, "SELECT * FROM generated_tasks WHERE id = ?", (task_id,))
    if row is None:
        return None
    row["difficulty_params"] = from_json_text(row.get("difficulty_params"), {})
    row["content_json"] = from_json_text(row.get("content_json"), {})
    row["quality_requirements"] = from_json_text(row.get("quality_requirements"), {})
    row["quality_check_result"] = from_json_text(row.get("quality_check_result"), {})
    return row


# --------------- 生成任务校验 ---------------

def create_task_validation(
    database_path: str | Path,
    task_id: int,
    validation_status: str,
    error_codes: list[str] | None = None,
    error_details: dict[str, Any] | None = None,
    attempt_number: int = 1,
    used_seed_fallback: bool = False,
) -> int:
    """写入生成任务校验记录，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO generated_task_validations
           (task_id, validation_status, error_codes, error_details, attempt_number, used_seed_fallback)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            task_id,
            validation_status,
            to_json_text(error_codes or []),
            to_json_text(error_details or {}),
            attempt_number,
            1 if used_seed_fallback else 0,
        ),
    )


# --------------- 学习证据 ---------------

def create_learning_evidence(
    database_path: str | Path,
    user_id: int,
    evidence_type: str,
    session_id: int | None = None,
    task_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    """写入学习证据，返回新记录 ID。原始证据只追加，不覆盖旧记录。"""
    return execute(
        database_path,
        """INSERT INTO learning_evidence (user_id, session_id, task_id, evidence_type, payload_json)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, session_id, task_id, evidence_type, to_json_text(payload or {})),
    )


def get_learning_evidence_by_user(
    database_path: str | Path, user_id: int, limit: int = 100
) -> list[dict[str, Any]]:
    """按用户查询学习证据。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM learning_evidence WHERE user_id = ? ORDER BY id ASC LIMIT ?",
        (user_id, limit),
    )
    for row in rows:
        row["payload_json"] = from_json_text(row.get("payload_json"), {})
    return rows


def get_learning_evidence_by_session(
    database_path: str | Path, session_id: int
) -> list[dict[str, Any]]:
    """按会话查询学习证据。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM learning_evidence WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    )
    for row in rows:
        row["payload_json"] = from_json_text(row.get("payload_json"), {})
    return rows


def get_learning_evidence_by_task(
    database_path: str | Path, task_id: int
) -> list[dict[str, Any]]:
    """按任务查询学习证据。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM learning_evidence WHERE task_id = ? ORDER BY id ASC",
        (task_id,),
    )
    for row in rows:
        row["payload_json"] = from_json_text(row.get("payload_json"), {})
    return rows


# --------------- 归属查询 helper ---------------

def get_generated_task_for_user(
    database_path: str | Path,
    *,
    user_id: int,
    task_id: int,
) -> dict[str, Any] | None:
    """按用户 ID 获取生成任务。只返回属于该用户的任务，其他用户或无任务返回 None。"""
    row = fetch_one(
        database_path,
        "SELECT * FROM generated_tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id),
    )
    if row is None:
        return None
    row["difficulty_params"] = from_json_text(row.get("difficulty_params"), {})
    row["content_json"] = from_json_text(row.get("content_json"), {})
    row["quality_requirements"] = from_json_text(row.get("quality_requirements"), {})
    row["quality_check_result"] = from_json_text(row.get("quality_check_result"), {})
    return row


def get_latest_training_submission_evidence(
    database_path: str | Path,
    *,
    task_id: int,
) -> dict[str, Any] | None:
    """获取指定任务的最新提交证据（按 created_at DESC, id DESC）。"""
    row = fetch_one(
        database_path,
        """SELECT * FROM learning_evidence
           WHERE task_id = ? AND evidence_type = 'TRAINING_ANSWER'
           ORDER BY created_at DESC, id DESC LIMIT 1""",
        (task_id,),
    )
    if row is None:
        return None
    row["payload_json"] = from_json_text(row.get("payload_json"), {})
    return row
