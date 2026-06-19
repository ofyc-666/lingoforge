"""工具调用和 Agent 决策日志 Repository。

为 tool_call_logs、agent_decision_logs 提供普通写入和查询能力。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.base import execute, fetch_all
from app.storage.json_fields import from_json_text, to_json_text


# --------------- 工具调用日志 ---------------

def create_tool_call_log(
    database_path: str | Path,
    call_name: str,
    call_type: str,
    input_json: dict[str, Any],
    output_json: dict[str, Any],
    status: str,
    user_id: int | None = None,
    session_id: int | None = None,
    error_code: str | None = None,
) -> int:
    """写入工具调用日志，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO tool_call_logs
           (user_id, session_id, call_name, call_type, input_json, output_json, status, error_code)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            session_id,
            call_name,
            call_type,
            to_json_text(input_json),
            to_json_text(output_json),
            status,
            error_code,
        ),
    )


def get_tool_logs_by_user(
    database_path: str | Path, user_id: int, limit: int = 100
) -> list[dict[str, Any]]:
    """按用户查询工具调用日志。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM tool_call_logs WHERE user_id = ? ORDER BY id ASC LIMIT ?",
        (user_id, limit),
    )
    for row in rows:
        row["input_json"] = from_json_text(row.get("input_json"), {})
        row["output_json"] = from_json_text(row.get("output_json"), {})
    return rows


def get_tool_logs_by_session(
    database_path: str | Path, session_id: int
) -> list[dict[str, Any]]:
    """按 session 查询工具调用日志。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM tool_call_logs WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    )
    for row in rows:
        row["input_json"] = from_json_text(row.get("input_json"), {})
        row["output_json"] = from_json_text(row.get("output_json"), {})
    return rows


def get_tool_logs_by_type(
    database_path: str | Path, call_type: str, limit: int = 100
) -> list[dict[str, Any]]:
    """按调用类型查询日志。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM tool_call_logs WHERE call_type = ? ORDER BY id ASC LIMIT ?",
        (call_type, limit),
    )
    for row in rows:
        row["input_json"] = from_json_text(row.get("input_json"), {})
        row["output_json"] = from_json_text(row.get("output_json"), {})
    return rows


# --------------- Agent 决策日志 ---------------

def create_agent_decision_log(
    database_path: str | Path,
    decision_type: str,
    user_id: int | None = None,
    session_id: int | None = None,
    input_summary: dict[str, Any] | None = None,
    decision: dict[str, Any] | None = None,
    evidence_refs: list[int] | None = None,
) -> int:
    """写入 Agent 决策日志，返回新记录 ID。"""
    return execute(
        database_path,
        """INSERT INTO agent_decision_logs
           (user_id, session_id, decision_type, input_summary_json, decision_json, evidence_refs)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            session_id,
            decision_type,
            to_json_text(input_summary or {}),
            to_json_text(decision or {}),
            to_json_text(evidence_refs or []),
        ),
    )


def get_agent_decisions_by_session(
    database_path: str | Path, session_id: int
) -> list[dict[str, Any]]:
    """按 session 查询 Agent 决策。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM agent_decision_logs WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    )
    for row in rows:
        row["input_summary_json"] = from_json_text(row.get("input_summary_json"), {})
        row["decision_json"] = from_json_text(row.get("decision_json"), {})
        row["evidence_refs"] = from_json_text(row.get("evidence_refs"), [])
    return rows
