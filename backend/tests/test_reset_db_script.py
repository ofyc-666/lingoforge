"""数据库重置脚本测试。"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from temp_paths import temp_db_path

# reset_db.py 脚本路径 (backend/scripts/)
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"

EXPECTED_TABLES = {
    "users", "user_goals", "profile_snapshots", "profile_update_suggestions",
    "vocabulary_items", "candidate_vocabulary_events", "skill_versions",
    "training_sessions", "generated_tasks", "generated_task_validations",
    "learning_evidence", "sidequest_runs", "sidequest_signals",
    "isolated_test_items", "isolated_test_attempts", "isolated_attempt_items",
    "tool_call_logs", "agent_decision_logs",
}


def table_names(database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def run_reset(db_path: str | Path) -> subprocess.CompletedProcess:
    """使用给定数据库路径运行 reset_db.py。"""
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(db_path)
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "reset_db.py")],
        capture_output=True,
        text=True,
        env=env,
    )


def test_reset_creates_core_tables():
    """reset 后核心表存在。"""
    db_path = temp_db_path("reset_script")
    result = run_reset(db_path)
    assert result.returncode == 0

    tables = table_names(db_path)
    assert EXPECTED_TABLES.issubset(tables)


def test_reset_is_repeatable():
    """重复执行不失败。"""
    db_path = temp_db_path("reset_repeat")
    r1 = run_reset(db_path)
    r2 = run_reset(db_path)
    assert r1.returncode == 0
    assert r2.returncode == 0

    tables = table_names(db_path)
    assert EXPECTED_TABLES.issubset(tables)


def test_reset_respects_database_path():
    """脚本尊重 DATABASE_PATH 环境变量。"""
    custom_path = temp_db_path("reset_custom")
    result = run_reset(custom_path)
    assert result.returncode == 0
    assert custom_path.exists()


def test_reset_output_no_secrets():
    """输出不包含任何密钥。"""
    db_path = temp_db_path("reset_secrets")
    # 设置一个假的 API key，确保不会泄露
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(db_path)
    env["DEEPSEEK_API_KEY"] = "sk-top-secret-key-12345"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "reset_db.py")],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "sk-top-secret-key-12345" not in result.stdout
    assert "sk-top-secret-key-12345" not in result.stderr


def test_reset_output_mentions_path():
    """输出包含数据库路径提示。"""
    db_path = temp_db_path("reset_path")
    result = run_reset(db_path)
    assert result.returncode == 0
    assert str(db_path) in result.stdout
