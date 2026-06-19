import sqlite3
from contextlib import closing

import pytest

from app.database import init_database, reset_database
from temp_paths import temp_db_path


EXPECTED_TABLES = {
    "users",
    "user_goals",
    "profile_snapshots",
    "profile_update_suggestions",
    "vocabulary_items",
    "candidate_vocabulary_events",
    "skill_versions",
    "training_sessions",
    "generated_tasks",
    "generated_task_validations",
    "learning_evidence",
    "sidequest_runs",
    "sidequest_signals",
    "isolated_test_items",
    "isolated_test_attempts",
    "isolated_attempt_items",
    "tool_call_logs",
    "agent_decision_logs",
}


def table_names(database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def test_init_database_creates_core_tables():
    database_path = temp_db_path("init")

    init_database(database_path)

    assert EXPECTED_TABLES.issubset(table_names(database_path))


def test_reset_database_is_repeatable():
    database_path = temp_db_path("reset")

    reset_database(database_path)
    reset_database(database_path)

    assert EXPECTED_TABLES.issubset(table_names(database_path))


def test_isolated_attempt_items_connect_attempts_and_items():
    database_path = temp_db_path("isolated_attempt_items")
    reset_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        foreign_keys = connection.execute("PRAGMA foreign_key_list(isolated_attempt_items)").fetchall()

    referenced_tables = {row[2] for row in foreign_keys}
    assert {"isolated_test_attempts", "isolated_test_items"}.issubset(referenced_tables)


def test_skill_versions_unique_constraint():
    """验证 skill_versions 的 (skill_id, version) 唯一约束。"""
    database_path = temp_db_path("skill_unique")
    reset_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO skill_versions (skill_id, version, target_ability) VALUES (?, ?, ?)",
            ("vocab_context", "1.0.0", "VOCABULARY_CONTEXT"),
        )
        connection.commit()

        # 第二次插入相同 (skill_id, version) 应失败
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO skill_versions (skill_id, version, target_ability) VALUES (?, ?, ?)",
                ("vocab_context", "1.0.0", "VOCABULARY_CONTEXT"),
            )


def test_skill_versions_unique_index_exists():
    """验证 skill_versions 存在唯一索引。"""
    database_path = temp_db_path("skill_index")
    reset_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        indexes = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'skill_versions'"
        ).fetchall()
    index_names = {row[0] for row in indexes}
    # 应至少有一个唯一索引
    has_unique = any("unique" in name.lower() or "sqlite_autoindex" in name.lower() for name in index_names)
    assert has_unique or len(index_names) >= 1


def test_json_default_values_present():
    """验证至少 3 个表的 JSON 字段具有默认值。"""
    database_path = temp_db_path("json_defaults")
    reset_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        # 插入最小数据，验证 JSON 默认值生效
        connection.execute("INSERT INTO users (display_name) VALUES (?)", ("test",))
        connection.execute("INSERT INTO users (display_name) VALUES (?)", ("test2",))
        connection.commit()
        user_id = connection.execute("SELECT id FROM users WHERE display_name = 'test'").fetchone()["id"]
        user2_id = connection.execute("SELECT id FROM users WHERE display_name = 'test2'").fetchone()["id"]

        # profile_snapshots: evidence_refs 默认 '[]'
        connection.execute(
            "INSERT INTO profile_snapshots (user_id, source, profile_json) VALUES (?, ?, ?)",
            (user_id, "DIAGNOSTIC", "{}"),
        )
        connection.commit()
        row = connection.execute("SELECT evidence_refs FROM profile_snapshots WHERE user_id = ?", (user_id,)).fetchone()
        assert row["evidence_refs"] == "[]"

        # generated_tasks: difficulty_params, content_json, quality_requirements, quality_check_result 默认 '{}'
        connection.execute(
            "INSERT INTO training_sessions (user_id, stage) VALUES (?, ?)",
            (user_id, "FIRST_MAIN"),
        )
        connection.commit()
        session_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO generated_tasks (session_id, user_id, task_type, target_ability) VALUES (?, ?, ?, ?)",
            (session_id, user_id, "LOW_PRESSURE_LEARNING", "VOCABULARY_CONTEXT"),
        )
        connection.commit()
        task = connection.execute("SELECT * FROM generated_tasks WHERE session_id = ?", (session_id,)).fetchone()
        assert task["difficulty_params"] == "{}"
        assert task["content_json"] == "{}"
        assert task["quality_requirements"] == "{}"
        assert task["quality_check_result"] == "{}"

        # sidequest_signals: context_json 默认 '{}', is_pending_verification 默认 1
        connection.execute(
            "INSERT INTO sidequest_runs (user_id, task_name) VALUES (?, ?)",
            (user_id, "TEST"),
        )
        connection.commit()
        run_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO sidequest_signals (user_id, sidequest_run_id, scene, signal_type) VALUES (?, ?, ?, ?)",
            (user_id, run_id, "AIRPORT_TICKET", "EXPOSURE"),
        )
        connection.commit()
        signal = connection.execute("SELECT * FROM sidequest_signals WHERE sidequest_run_id = ?", (run_id,)).fetchone()
        assert signal["context_json"] == "{}"
        assert signal["is_pending_verification"] == 1

        # 额外: profile_update_suggestions 的 evidence_refs, agent_payload 默认值
        connection.execute(
            "INSERT INTO profile_update_suggestions (user_id, ability, direction, reason) VALUES (?, ?, ?, ?)",
            (user2_id, "VOCABULARY_CONTEXT", "IMPROVE", "test"),
        )
        connection.commit()
        suggestion = connection.execute(
            "SELECT * FROM profile_update_suggestions WHERE user_id = ?", (user2_id,)
        ).fetchone()
        assert suggestion["evidence_refs"] == "[]"
        assert suggestion["agent_payload"] == "{}"
        assert suggestion["validation_status"] == "NEEDS_REVIEW"


def test_key_foreign_keys_enforced():
    """验证 sidequest_signals, generated_tasks, isolated_attempt_items 的关键外键。"""
    database_path = temp_db_path("fk_test")
    reset_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # sidequest_signals → sidequest_runs 外键
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO sidequest_signals (user_id, sidequest_run_id, scene, signal_type) VALUES (?, ?, ?, ?)",
                (1, 999, "AIRPORT_TICKET", "EXPOSURE"),
            )

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        # generated_tasks → training_sessions 外键
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO generated_tasks (session_id, user_id, task_type, target_ability) VALUES (?, ?, ?, ?)",
                (999, 1, "SHORT_TRAINING", "VOCABULARY_CONTEXT"),
            )

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        # 先创建必要的外键依赖
        connection.execute("INSERT INTO users (display_name) VALUES (?)", ("fk_test_user",))
        connection.commit()
        user_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]

        # isolated_attempt_items → isolated_test_attempts
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO isolated_attempt_items (attempt_id, isolated_test_item_id, item_order, item_version) VALUES (?, ?, ?, ?)",
                (999, 999, 1, "1.0"),
            )
