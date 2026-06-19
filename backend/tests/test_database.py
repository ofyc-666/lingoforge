import sqlite3
from contextlib import closing

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
