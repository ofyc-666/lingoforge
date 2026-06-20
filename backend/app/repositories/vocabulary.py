"""词汇、Skill 元数据和候选词 Repository。

为 vocabulary_items、skill_versions、candidate_vocabulary_events
提供普通写入与查询。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all, fetch_one
from app.storage.json_fields import from_json_text, to_json_text


# --------------- 词汇项 ---------------

def create_vocabulary_item(
    database_path: str | Path,
    text: str,
    meaning_zh: str | None = None,
    part_of_speech: str | None = None,
    tags: list[str] | None = None,
    source_type: str = "CET6_VOCAB",
) -> int:
    """创建词汇项，返回新记录 ID。"""
    return execute(
        database_path,
        "INSERT INTO vocabulary_items (text, meaning_zh, part_of_speech, tags, source_type) VALUES (?, ?, ?, ?, ?)",
        (text, meaning_zh, part_of_speech, to_json_text(tags or []), source_type),
    )


def get_vocabulary_by_text(database_path: str | Path, text: str) -> dict[str, Any] | None:
    """按文本查找词汇项（用于去重）。"""
    row = fetch_one(database_path, "SELECT * FROM vocabulary_items WHERE text = ?", (text,))
    if row is None:
        return None
    row["tags"] = from_json_text(row.get("tags"), [])
    return row


def list_all_vocabulary(database_path: str | Path) -> list[dict[str, Any]]:
    """列出所有词汇项。"""
    rows = fetch_all(database_path, "SELECT * FROM vocabulary_items ORDER BY id ASC")
    for row in rows:
        row["tags"] = from_json_text(row.get("tags"), [])
    return rows


def get_vocabulary_item(database_path: str | Path, item_id: int) -> dict[str, Any] | None:
    """按 ID 获取词汇项。"""
    row = fetch_one(database_path, "SELECT * FROM vocabulary_items WHERE id = ?", (item_id,))
    if row is None:
        return None
    row["tags"] = from_json_text(row.get("tags"), [])
    return row


def list_vocabulary_by_tag(database_path: str | Path, tag: str) -> list[dict[str, Any]]:
    """按标签列出词汇项。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM vocabulary_items WHERE tags LIKE ? ORDER BY id ASC",
        (f'%"{tag}"%',),
    )
    for row in rows:
        row["tags"] = from_json_text(row.get("tags"), [])
    return rows


def list_vocabulary_by_source(database_path: str | Path, source_type: str) -> list[dict[str, Any]]:
    """按来源类型列出词汇项。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM vocabulary_items WHERE source_type = ? ORDER BY id ASC",
        (source_type,),
    )
    for row in rows:
        row["tags"] = from_json_text(row.get("tags"), [])
    return rows


# --------------- Skill 版本 ---------------

def create_skill_version(
    database_path: str | Path,
    skill_id: str,
    version: str,
    target_ability: str,
    applicable_conditions: dict[str, Any] | None = None,
    difficulty_params: dict[str, Any] | None = None,
    generation_rules: dict[str, Any] | None = None,
    quality_requirements: dict[str, Any] | None = None,
    observable_evidence: dict[str, Any] | None = None,
    common_error_types: list[str] | None = None,
) -> int:
    """创建 Skill 版本元数据，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO skill_versions
           (skill_id, version, target_ability, applicable_conditions, difficulty_params,
            generation_rules, quality_requirements, observable_evidence, common_error_types)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            skill_id,
            version,
            target_ability,
            to_json_text(applicable_conditions or {}),
            to_json_text(difficulty_params or {}),
            to_json_text(generation_rules or {}),
            to_json_text(quality_requirements or {}),
            to_json_text(observable_evidence or {}),
            to_json_text(common_error_types or []),
        ),
    )


def get_skill_version(
    database_path: str | Path, skill_id: str, version: str
) -> dict[str, Any] | None:
    """按 skill_id 和 version 获取 Skill 元数据。"""
    row = fetch_one(
        database_path,
        "SELECT * FROM skill_versions WHERE skill_id = ? AND version = ?",
        (skill_id, version),
    )
    if row is None:
        return None
    row["applicable_conditions"] = from_json_text(row.get("applicable_conditions"), {})
    row["difficulty_params"] = from_json_text(row.get("difficulty_params"), {})
    row["generation_rules"] = from_json_text(row.get("generation_rules"), {})
    row["quality_requirements"] = from_json_text(row.get("quality_requirements"), {})
    row["observable_evidence"] = from_json_text(row.get("observable_evidence"), {})
    row["common_error_types"] = from_json_text(row.get("common_error_types"), [])
    return row


# --------------- 候选词事件 ---------------

def create_candidate_event(
    database_path: str | Path,
    user_id: int,
    workflow_stage: str,
    ability: str | None = None,
    candidate_items: list[dict[str, Any]] | None = None,
    included_sidequest_signal_ids: list[int] | None = None,
    selection_reason: str | None = None,
) -> int:
    """写入候选词事件，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO candidate_vocabulary_events
           (user_id, workflow_stage, ability, candidate_items,
            included_sidequest_signal_ids, selection_reason)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            workflow_stage,
            ability,
            to_json_text(candidate_items or []),
            to_json_text(included_sidequest_signal_ids or []),
            selection_reason,
        ),
    )


def get_recent_candidate_events(
    database_path: str | Path,
    user_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """读取用户最近候选词事件（按创建时间升序）。"""
    rows = fetch_all(
        database_path,
        """SELECT * FROM candidate_vocabulary_events
           WHERE user_id = ?
           ORDER BY created_at DESC, id DESC
           LIMIT ?""",
        (user_id, limit),
    )
    rows.reverse()
    for row in rows:
        row["candidate_items"] = from_json_text(row.get("candidate_items"), [])
        row["included_sidequest_signal_ids"] = from_json_text(
            row.get("included_sidequest_signal_ids"), []
        )
    return rows
