"""Repository 基础数据库辅助测试。"""

from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from app.database import connect
from app.repositories.base import execute, fetch_all, fetch_one, row_to_dict
from temp_paths import temp_db_path


@pytest.fixture
def test_db():
    """创建临时测试数据库，包含简单测试表。"""
    db_path = temp_db_path("repo_base")
    with closing(connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
    return db_path


class TestRowToDict:
    """row_to_dict 测试。"""

    def test_converts_row_to_dict(self, test_db):
        with closing(connect(test_db)) as conn:
            conn.execute("INSERT INTO test_items (name, value) VALUES (?, ?)", ("alpha", 42))
            conn.commit()
            row = conn.execute("SELECT * FROM test_items WHERE name = ?", ("alpha",)).fetchone()

        result = row_to_dict(row)
        assert result == {"id": 1, "name": "alpha", "value": 42}

    def test_none_returns_none(self):
        assert row_to_dict(None) is None


class TestFetchOne:
    """fetch_one 测试。"""

    def test_returns_dict_for_existing_row(self, test_db):
        with closing(connect(test_db)) as conn:
            conn.execute("INSERT INTO test_items (name, value) VALUES (?, ?)", ("alpha", 42))
            conn.commit()

        result = fetch_one(test_db, "SELECT * FROM test_items WHERE name = ?", ("alpha",))
        assert result == {"id": 1, "name": "alpha", "value": 42}

    def test_returns_none_for_missing_row(self, test_db):
        result = fetch_one(test_db, "SELECT * FROM test_items WHERE name = ?", ("nope",))
        assert result is None

    def test_accepts_str_path(self, test_db):
        result = fetch_one(str(test_db), "SELECT 1 AS n", ())
        assert result == {"n": 1}


class TestFetchAll:
    """fetch_all 测试。"""

    def test_returns_list_of_dicts(self, test_db):
        with closing(connect(test_db)) as conn:
            conn.execute("INSERT INTO test_items (name, value) VALUES (?, ?)", ("a", 1))
            conn.execute("INSERT INTO test_items (name, value) VALUES (?, ?)", ("b", 2))
            conn.commit()

        results = fetch_all(test_db, "SELECT * FROM test_items ORDER BY id")
        assert len(results) == 2
        assert results[0]["name"] == "a"
        assert results[1]["name"] == "b"

    def test_returns_empty_list_for_no_rows(self, test_db):
        results = fetch_all(test_db, "SELECT * FROM test_items WHERE name = ?", ("nope",))
        assert results == []

    def test_accepts_str_path(self, test_db):
        results = fetch_all(str(test_db), "SELECT 1 AS n UNION SELECT 2 ORDER BY n")
        assert results == [{"n": 1}, {"n": 2}]


class TestExecute:
    """execute 测试。"""

    def test_insert_returns_lastrowid(self, test_db):
        rowid = execute(test_db, "INSERT INTO test_items (name, value) VALUES (?, ?)", ("gamma", 99))
        assert rowid >= 1
        row = fetch_one(test_db, "SELECT * FROM test_items WHERE id = ?", (rowid,))
        assert row is not None
        assert row["name"] == "gamma"

    def test_insert_commits(self, test_db):
        rowid = execute(test_db, "INSERT INTO test_items (name, value) VALUES (?, ?)", ("gamma", 99))
        row = fetch_one(test_db, "SELECT * FROM test_items WHERE name = ?", ("gamma",))
        assert row is not None
        assert row["value"] == 99

    def test_update_commits(self, test_db):
        execute(test_db, "INSERT INTO test_items (name, value) VALUES (?, ?)", ("delta", 10))
        execute(test_db, "UPDATE test_items SET value = ? WHERE name = ?", (20, "delta"))
        row = fetch_one(test_db, "SELECT * FROM test_items WHERE name = ?", ("delta",))
        assert row["value"] == 20

    def test_delete_commits(self, test_db):
        execute(test_db, "INSERT INTO test_items (name, value) VALUES (?, ?)", ("eps", 1))
        execute(test_db, "DELETE FROM test_items WHERE name = ?", ("eps",))
        row = fetch_one(test_db, "SELECT * FROM test_items WHERE name = ?", ("eps",))
        assert row is None

    def test_accepts_str_path(self, test_db):
        execute(str(test_db), "INSERT INTO test_items (name, value) VALUES (?, ?)", ("zeta", 7))
        row = fetch_one(test_db, "SELECT * FROM test_items WHERE name = ?", ("zeta",))
        assert row["value"] == 7


class TestForeignKeyEnforcement:
    """外键约束测试。"""

    def test_foreign_keys_are_enabled(self, test_db):
        # 通过 database.connect 验证外键已启用
        path = temp_db_path("repo_fk")
        with closing(connect(path)) as conn:
            conn.execute("""
                CREATE TABLE parent (id INTEGER PRIMARY KEY)
            """)
            conn.execute("""
                CREATE TABLE child (
                    id INTEGER PRIMARY KEY,
                    parent_id INTEGER REFERENCES parent(id)
                )
            """)
            conn.commit()

        # 插入违反外键约束的记录应失败
        with pytest.raises(sqlite3.IntegrityError):
            execute(path, "INSERT INTO child (parent_id) VALUES (?)", (999,))
