"""副线运行和副线信号 Repository。

为 sidequest_runs、sidequest_signals 提供普通写入和查询能力。
不写入画像或正式证据表。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all
from app.storage.json_fields import from_json_text, to_json_text


# --------------- 副线运行 ---------------

def create_sidequest_run(
    database_path: str | Path,
    user_id: int,
    task_name: str,
    objective: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> int:
    """创建副线运行记录，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO sidequest_runs (user_id, task_name, objective_json, result_json)
           VALUES (?, ?, ?, ?)""",
        (user_id, task_name, to_json_text(objective or {}), to_json_text(result or {})),
    )


# --------------- 副线信号 ---------------

def create_sidequest_signal(
    database_path: str | Path,
    user_id: int,
    sidequest_run_id: int,
    scene: str,
    signal_type: str,
    vocabulary_item_id: int | None = None,
    expression_text: str | None = None,
    context_json: dict[str, Any] | None = None,
) -> int:
    """写入一条副线信号，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO sidequest_signals
           (user_id, sidequest_run_id, scene, vocabulary_item_id, expression_text,
            context_json, signal_type)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            sidequest_run_id,
            scene,
            vocabulary_item_id,
            expression_text,
            to_json_text(context_json or {}),
            signal_type,
        ),
    )


def get_pending_signals(
    database_path: str | Path, user_id: int
) -> list[dict[str, Any]]:
    """按用户读取待验证副线信号。"""
    rows = fetch_all(
        database_path,
        """SELECT * FROM sidequest_signals
           WHERE user_id = ? AND is_pending_verification = 1
           ORDER BY id ASC""",
        (user_id,),
    )
    for row in rows:
        row["context_json"] = from_json_text(row.get("context_json"), {})
    return rows


def get_signals_by_run(
    database_path: str | Path, run_id: int
) -> list[dict[str, Any]]:
    """按 run ID 读取信号。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM sidequest_signals WHERE sidequest_run_id = ? ORDER BY id ASC",
        (run_id,),
    )
    for row in rows:
        row["context_json"] = from_json_text(row.get("context_json"), {})
    return rows
