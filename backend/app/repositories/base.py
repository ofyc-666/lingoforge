"""Repository 基础数据库辅助。

为 repository 提供薄封装，减少重复 SQL 样板。
不持有全局连接，不引入 ORM。
"""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
from typing import Any

from app.database import connect


def row_to_dict(row: Any) -> dict[str, Any] | None:
    """将 sqlite3.Row 转为 dict，None 返回 None。"""
    if row is None:
        return None
    return dict(row)


def fetch_one(
    database_path: str | Path,
    sql: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    """执行查询并返回单行 dict，不存在时返回 None。"""
    with closing(connect(database_path)) as conn:
        row = conn.execute(sql, params).fetchone()
    return row_to_dict(row)


def fetch_all(
    database_path: str | Path,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """执行查询并返回所有行 dict 列表，不存在时返回空列表。"""
    with closing(connect(database_path)) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def execute(
    database_path: str | Path,
    sql: str,
    params: tuple[Any, ...] = (),
) -> int:
    """执行写入操作并提交，返回 lastrowid。"""
    with closing(connect(database_path)) as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
