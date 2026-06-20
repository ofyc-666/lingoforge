"""MVP 逻辑记忆服务。

为避免在本轮引入新表，最小记忆项写入 agent_decision_logs：
decision_type="MEMORY_ITEM"，decision_json 保存 MemoryItem 逻辑对象。
这满足 MVP 的读取、写入、状态和可追溯性语义，后续可迁移到 memory_items 表。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.base import fetch_all
from app.repositories.logs import create_agent_decision_log
from app.storage.json_fields import from_json_text

VALID_MEMORY_STATUSES = {"ACTIVE", "NEEDS_REVIEW", "DISPUTED", "SUPERSEDED"}


def write_memory_item(
    database_path: str | Path,
    *,
    user_id: int,
    session_id: int | None = None,
    memory_type: str,
    content: dict[str, Any],
    source_refs: list[dict[str, Any]],
    status: str = "ACTIVE",
    supersedes_refs: list[int] | None = None,
    disputes_refs: list[int] | None = None,
) -> int:
    """写入一条逻辑记忆项，返回承载该记忆的日志 ID。"""
    if status not in VALID_MEMORY_STATUSES:
        raise ValueError("INVALID_MEMORY_STATUS")
    return create_agent_decision_log(
        database_path,
        decision_type="MEMORY_ITEM",
        user_id=user_id,
        session_id=session_id,
        input_summary={
            "source": "memory_service_mvp",
            "source_refs": source_refs,
        },
        decision={
            "memory_type": memory_type,
            "status": status,
            "content": content,
            "source_refs": source_refs,
            "supersedes_refs": supersedes_refs or [],
            "disputes_refs": disputes_refs or [],
            "storage": "agent_decision_logs",
        },
        evidence_refs=[
            int(ref["id"])
            for ref in source_refs
            if ref.get("type") == "learning_evidence" and isinstance(ref.get("id"), int)
        ],
    )


def list_memory_items(
    database_path: str | Path,
    *,
    user_id: int,
    statuses: tuple[str, ...] = ("ACTIVE", "NEEDS_REVIEW"),
    limit: int = 20,
) -> list[dict[str, Any]]:
    """读取当前用户的逻辑记忆项，按创建顺序返回最近 limit 条。"""
    rows = fetch_all(
        database_path,
        """SELECT id, decision_json, created_at
           FROM agent_decision_logs
           WHERE user_id = ? AND decision_type = 'MEMORY_ITEM'
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit),
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        memory = from_json_text(row.get("decision_json"), {})
        if not isinstance(memory, dict):
            continue
        if memory.get("status") not in statuses:
            continue
        items.append({
            "memory_id": row["id"],
            "created_at": row.get("created_at"),
            **memory,
        })
    items.reverse()
    return items
