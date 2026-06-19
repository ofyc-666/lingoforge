"""用户、目标和画像 Repository。

为 users、user_goals、profile_snapshots、profile_update_suggestions
提供普通 CRUD 和简单查询。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all, fetch_one
from app.storage.json_fields import from_json_text, to_json_text


# --------------- 用户 ---------------

def create_user(database_path: str | Path, display_name: str) -> int:
    """创建用户，返回新用户 ID。"""
    return execute(
        database_path,
        "INSERT INTO users (display_name) VALUES (?)",
        (display_name,),
    )


def get_user(database_path: str | Path, user_id: int) -> dict[str, Any] | None:
    """按 ID 获取用户。"""
    return fetch_one(database_path, "SELECT * FROM users WHERE id = ?", (user_id,))


# --------------- 用户目标 ---------------

def save_user_goal(
    database_path: str | Path,
    user_id: int,
    exam_type: str = "CET-6",
    days_until_exam: int | None = None,
    target_score: int | None = None,
    daily_minutes: int | None = None,
    self_reported_weaknesses: list[str] | None = None,
    interest_topics: list[str] | None = None,
) -> int:
    """保存用户目标，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO user_goals
           (user_id, exam_type, days_until_exam, target_score, daily_minutes,
            self_reported_weaknesses, interest_topics)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            exam_type,
            days_until_exam,
            target_score,
            daily_minutes,
            to_json_text(self_reported_weaknesses or []),
            to_json_text(interest_topics or []),
        ),
    )


def get_latest_user_goal(database_path: str | Path, user_id: int) -> dict[str, Any] | None:
    """获取用户最新目标。"""
    row = fetch_one(
        database_path,
        "SELECT * FROM user_goals WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    if row is None:
        return None
    row["self_reported_weaknesses"] = from_json_text(row.get("self_reported_weaknesses"), [])
    row["interest_topics"] = from_json_text(row.get("interest_topics"), [])
    return row


# --------------- 画像快照 ---------------

def create_profile_snapshot(
    database_path: str | Path,
    user_id: int,
    source: str,
    profile: dict[str, Any],
    evidence_refs: list[int] | None = None,
) -> int:
    """创建画像快照，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO profile_snapshots (user_id, source, profile_json, evidence_refs)
           VALUES (?, ?, ?, ?)""",
        (user_id, source, to_json_text(profile), to_json_text(evidence_refs or [])),
    )


def get_latest_profile(database_path: str | Path, user_id: int) -> dict[str, Any] | None:
    """获取用户最新画像快照。"""
    row = fetch_one(
        database_path,
        "SELECT * FROM profile_snapshots WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    if row is None:
        return None
    row["profile_json"] = from_json_text(row.get("profile_json"), {})
    row["evidence_refs"] = from_json_text(row.get("evidence_refs"), [])
    return row


# --------------- 画像更新建议 ---------------

def create_profile_suggestion(
    database_path: str | Path,
    user_id: int,
    ability: str,
    direction: str,
    reason: str,
    evidence_refs: list[int] | None = None,
    agent_payload: dict[str, Any] | None = None,
) -> int:
    """写入画像更新建议，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO profile_update_suggestions
           (user_id, ability, direction, reason, evidence_refs, agent_payload)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            ability,
            direction,
            reason,
            to_json_text(evidence_refs or []),
            to_json_text(agent_payload or {}),
        ),
    )


def get_user_profile_suggestions(
    database_path: str | Path, user_id: int
) -> list[dict[str, Any]]:
    """按用户读取画像建议列表（按创建时间升序）。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM profile_update_suggestions WHERE user_id = ? ORDER BY id ASC",
        (user_id,),
    )
    for row in rows:
        row["evidence_refs"] = from_json_text(row.get("evidence_refs"), [])
        row["agent_payload"] = from_json_text(row.get("agent_payload"), {})
    return rows
