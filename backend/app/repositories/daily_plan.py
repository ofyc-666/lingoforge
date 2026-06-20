"""每日学习计划、背词事件和词汇状态 Repository。"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all, fetch_one
from app.storage.json_fields import from_json_text, to_json_text


# --------------- 每日学习计划 ---------------

def create_daily_plan(
    database_path: str | Path,
    *,
    user_id: int,
    session_id: int | None,
    plan_date: str,
    status: str = "PLANNED",
    practice_mode: str = "TARGETED_PRACTICE",
    target_abilities: list[str] | None = None,
    selected_skills: list[dict[str, Any]] | None = None,
    difficulty_params: dict[str, Any] | None = None,
    hint_strategy: dict[str, Any] | None = None,
    rationale: str = "",
    estimated_minutes: int | None = None,
    candidate_event_id: int | None = None,
    agent_decision_log_id: int | None = None,
) -> int:
    return execute(
        database_path,
        """INSERT INTO daily_learning_plans
           (user_id, session_id, plan_date, status, practice_mode,
            target_abilities, selected_skills, difficulty_params, hint_strategy,
            rationale, estimated_minutes, candidate_event_id, agent_decision_log_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, session_id, plan_date, status, practice_mode,
            to_json_text(target_abilities or []),
            to_json_text(selected_skills or []),
            to_json_text(difficulty_params or {}),
            to_json_text(hint_strategy or {}),
            rationale, estimated_minutes, candidate_event_id, agent_decision_log_id,
        ),
    )


def get_daily_plan(database_path: str | Path, plan_id: int) -> dict[str, Any] | None:
    row = fetch_one(database_path, "SELECT * FROM daily_learning_plans WHERE id = ?", (plan_id,))
    if row is None:
        return None
    return _deserialize_plan(row)


def get_today_plan(database_path: str | Path, user_id: int, plan_date: str) -> dict[str, Any] | None:
    row = fetch_one(
        database_path,
        "SELECT * FROM daily_learning_plans WHERE user_id = ? AND plan_date = ? ORDER BY id DESC LIMIT 1",
        (user_id, plan_date),
    )
    if row is None:
        return None
    return _deserialize_plan(row)


def update_plan_status(database_path: str | Path, plan_id: int, status: str) -> None:
    execute(
        database_path,
        "UPDATE daily_learning_plans SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.datetime.now(datetime.timezone.utc).isoformat(), plan_id),
    )


def _deserialize_plan(row: dict[str, Any]) -> dict[str, Any]:
    row["target_abilities"] = from_json_text(row.get("target_abilities"), [])
    row["selected_skills"] = from_json_text(row.get("selected_skills"), [])
    row["difficulty_params"] = from_json_text(row.get("difficulty_params"), {})
    row["hint_strategy"] = from_json_text(row.get("hint_strategy"), {})
    return row


# --------------- 计划词汇关联 ---------------

def add_plan_vocabulary_item(
    database_path: str | Path,
    *,
    plan_id: int,
    vocabulary_item_id: int,
    word_role: str,
    item_order: int = 0,
    selection_reason: str = "",
) -> int:
    return execute(
        database_path,
        """INSERT INTO daily_plan_vocabulary_items
           (plan_id, vocabulary_item_id, word_role, item_order, selection_reason)
           VALUES (?, ?, ?, ?, ?)""",
        (plan_id, vocabulary_item_id, word_role, item_order, selection_reason),
    )


def get_plan_vocabulary_items(
    database_path: str | Path,
    plan_id: int,
) -> list[dict[str, Any]]:
    return fetch_all(
        database_path,
        "SELECT * FROM daily_plan_vocabulary_items WHERE plan_id = ? ORDER BY item_order ASC",
        (plan_id,),
    )


# --------------- 用户词汇状态 ---------------

def upsert_user_vocabulary_state(
    database_path: str | Path,
    *,
    user_id: int,
    vocabulary_item_id: int,
    learning_status: str = "NEW",
    familiarity_level: str = "UNKNOWN",
    first_seen_at: str | None = None,
    last_reviewed_at: str | None = None,
    last_success_at: str | None = None,
    next_review_at: str | None = None,
    correct_count: int = 0,
    wrong_count: int = 0,
    context_error_count: int = 0,
    consecutive_correct: int = 0,
    consecutive_wrong: int = 0,
    prompt_dependency: str = "LOW",
    evidence_refs: list[int] | None = None,
    algorithm_version: str = "mvp-v1",
) -> int:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    existing = fetch_one(
        database_path,
        "SELECT id FROM user_vocabulary_states WHERE user_id = ? AND vocabulary_item_id = ?",
        (user_id, vocabulary_item_id),
    )
    if existing is not None:
        execute(
            database_path,
            """UPDATE user_vocabulary_states
               SET learning_status = ?, familiarity_level = ?,
                   last_reviewed_at = ?, last_success_at = ?, next_review_at = ?,
                   correct_count = ?, wrong_count = ?, context_error_count = ?,
                   consecutive_correct = ?, consecutive_wrong = ?,
                   prompt_dependency = ?, evidence_refs = ?,
                   algorithm_version = ?, updated_at = ?
               WHERE id = ?""",
            (
                learning_status, familiarity_level,
                last_reviewed_at, last_success_at, next_review_at,
                max(0, correct_count), max(0, wrong_count), max(0, context_error_count),
                max(0, consecutive_correct), max(0, consecutive_wrong),
                prompt_dependency, to_json_text(evidence_refs or []),
                algorithm_version, now,
                existing["id"],
            ),
        )
        return existing["id"]
    else:
        return execute(
            database_path,
            """INSERT INTO user_vocabulary_states
               (user_id, vocabulary_item_id, learning_status, familiarity_level,
                first_seen_at, last_reviewed_at, last_success_at, next_review_at,
                correct_count, wrong_count, context_error_count,
                consecutive_correct, consecutive_wrong,
                prompt_dependency, evidence_refs, algorithm_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, vocabulary_item_id, learning_status, familiarity_level,
                first_seen_at or now, last_reviewed_at, last_success_at, next_review_at,
                max(0, correct_count), max(0, wrong_count), max(0, context_error_count),
                max(0, consecutive_correct), max(0, consecutive_wrong),
                prompt_dependency, to_json_text(evidence_refs or []), algorithm_version,
            ),
        )


def get_user_vocabulary_state(
    database_path: str | Path,
    user_id: int,
    vocabulary_item_id: int,
) -> dict[str, Any] | None:
    row = fetch_one(
        database_path,
        "SELECT * FROM user_vocabulary_states WHERE user_id = ? AND vocabulary_item_id = ?",
        (user_id, vocabulary_item_id),
    )
    if row is None:
        return None
    row["evidence_refs"] = from_json_text(row.get("evidence_refs"), [])
    return row


def get_all_user_vocabulary_states(
    database_path: str | Path,
    user_id: int,
) -> list[dict[str, Any]]:
    rows = fetch_all(
        database_path,
        "SELECT * FROM user_vocabulary_states WHERE user_id = ?",
        (user_id,),
    )
    for row in rows:
        row["evidence_refs"] = from_json_text(row.get("evidence_refs"), [])
    return rows


# --------------- 背词事件 ---------------

def create_review_event(
    database_path: str | Path,
    *,
    user_id: int,
    vocabulary_item_id: int,
    event_type: str,
    session_id: int | None = None,
    plan_id: int | None = None,
    answer_json: dict[str, Any] | None = None,
    is_correct: bool | None = None,
    self_rating: str | None = None,
    used_hint: bool = False,
    time_spent_seconds: int | None = None,
    evidence_refs: list[int] | None = None,
    metadata_json: dict[str, Any] | None = None,
    occurred_at: str | None = None,
) -> int:
    return execute(
        database_path,
        """INSERT INTO vocabulary_review_events
           (user_id, vocabulary_item_id, event_type, session_id, plan_id,
            answer_json, is_correct, self_rating, used_hint,
            time_spent_seconds, evidence_refs, metadata_json, occurred_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, vocabulary_item_id, event_type, session_id, plan_id,
            to_json_text(answer_json or {}),
            1 if is_correct is True else (0 if is_correct is False else None),
            self_rating,
            1 if used_hint else 0,
            time_spent_seconds,
            to_json_text(evidence_refs or []),
            to_json_text(metadata_json or {}),
            occurred_at or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        ),
    )


def get_review_events_for_plan(
    database_path: str | Path,
    plan_id: int,
    user_id: int,
) -> list[dict[str, Any]]:
    rows = fetch_all(
        database_path,
        """SELECT * FROM vocabulary_review_events
           WHERE plan_id = ? AND user_id = ?
           ORDER BY occurred_at ASC""",
        (plan_id, user_id),
    )
    for row in rows:
        row["answer_json"] = from_json_text(row.get("answer_json"), {})
        row["evidence_refs"] = from_json_text(row.get("evidence_refs"), [])
        row["metadata_json"] = from_json_text(row.get("metadata_json"), {})
    return rows
