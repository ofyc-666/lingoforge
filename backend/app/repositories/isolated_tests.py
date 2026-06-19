"""隔离检测题与尝试 Repository。

为 isolated_test_items、isolated_test_attempts、isolated_attempt_items
提供普通 CRUD 和连接关系查询。
只做数据访问，不做隔离权限裁决。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all, fetch_one
from app.storage.json_fields import from_json_text, to_json_text


# --------------- 隔离题 ---------------

def create_isolated_test_item(
    database_path: str | Path,
    target_ability: str,
    item_version: str,
    item_payload: dict[str, Any],
    answer_key: dict[str, Any],
    answer_rationale: dict[str, Any] | None = None,
    distractor_rationale: dict[str, Any] | None = None,
    is_active: bool = True,
) -> int:
    """创建隔离题，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO isolated_test_items
           (target_ability, item_version, item_payload, answer_key,
            answer_rationale, distractor_rationale, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            target_ability,
            item_version,
            to_json_text(item_payload),
            to_json_text(answer_key),
            to_json_text(answer_rationale or {}),
            to_json_text(distractor_rationale or {}),
            1 if is_active else 0,
        ),
    )


def list_active_items_by_ability(
    database_path: str | Path, ability: str
) -> list[dict[str, Any]]:
    """按能力列出 active 隔离题。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM isolated_test_items WHERE target_ability = ? AND is_active = 1 ORDER BY id ASC",
        (ability,),
    )
    for row in rows:
        row["item_payload"] = from_json_text(row.get("item_payload"), {})
        row["answer_key"] = from_json_text(row.get("answer_key"), {})
        row["answer_rationale"] = from_json_text(row.get("answer_rationale"), {})
        row["distractor_rationale"] = from_json_text(row.get("distractor_rationale"), {})
    return rows


# --------------- 隔离检测尝试 ---------------

def create_isolated_test_attempt(
    database_path: str | Path,
    user_id: int,
    session_id: int | None = None,
    user_answers: dict[str, Any] | None = None,
    score_json: dict[str, Any] | None = None,
    time_spent_seconds: int | None = None,
) -> int:
    """创建隔离检测尝试，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO isolated_test_attempts
           (user_id, session_id, user_answers, score_json, time_spent_seconds)
           VALUES (?, ?, ?, ?, ?)""",
        (
            user_id,
            session_id,
            to_json_text(user_answers or {}),
            to_json_text(score_json or {}),
            time_spent_seconds,
        ),
    )


# --------------- 连接表 ---------------

def add_item_to_attempt(
    database_path: str | Path,
    attempt_id: int,
    item_id: int,
    item_order: int,
    item_version: str,
) -> int:
    """关联 attempt 和 item，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO isolated_attempt_items
           (attempt_id, isolated_test_item_id, item_order, item_version)
           VALUES (?, ?, ?, ?)""",
        (attempt_id, item_id, item_order, item_version),
    )


def get_items_for_attempt(
    database_path: str | Path, attempt_id: int
) -> list[dict[str, Any]]:
    """读取 attempt 的 item 列表（按 item_order 排序）。"""
    return fetch_all(
        database_path,
        """SELECT * FROM isolated_attempt_items
           WHERE attempt_id = ? ORDER BY item_order ASC""",
        (attempt_id,),
    )


def get_attempt_with_items(
    database_path: str | Path, attempt_id: int
) -> dict[str, Any] | None:
    """读取 attempt 及其关联的 item 列表。"""
    attempt = fetch_one(
        database_path,
        "SELECT * FROM isolated_test_attempts WHERE id = ?",
        (attempt_id,),
    )
    if attempt is None:
        return None
    attempt["user_answers"] = from_json_text(attempt.get("user_answers"), {})
    attempt["score_json"] = from_json_text(attempt.get("score_json"), {})
    items = get_items_for_attempt(database_path, attempt_id)
    return {"attempt": attempt, "items": items}
