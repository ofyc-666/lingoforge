"""演示数据种子脚本测试。"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from app.database import init_database
from app.repositories.base import fetch_all, fetch_one
from app.repositories.training import get_generated_task
from app.repositories.users import get_user
from temp_paths import temp_db_path


def _run_seed(db_path: str) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[2] / "scripts" / "seed_demo.py"
    return subprocess.run(
        [sys.executable, str(script), "--database-path", db_path],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestDemoSeedScript:
    """演示数据种子脚本测试。"""

    def test_script_creates_core_data(self):
        db_path = str(temp_db_path("demo_seed"))
        init_database(db_path)

        result = _run_seed(db_path)
        assert result.returncode == 0, f"stderr:\n{result.stderr}"

        output = result.stdout
        assert "user_id" in output.lower() or "用户" in output
        assert "session_id" in output.lower() or "会话" in output
        assert "task_id" in output.lower() or "任务" in output

        # 验证数据库中有数据
        users = fetch_all(db_path, "SELECT * FROM users")
        assert len(users) >= 1

        goals = fetch_all(db_path, "SELECT * FROM user_goals")
        assert len(goals) >= 1

        snapshots = fetch_all(db_path, "SELECT * FROM profile_snapshots")
        assert len(snapshots) >= 1

        vocabulary = fetch_all(db_path, "SELECT * FROM vocabulary_items")
        assert len(vocabulary) >= 1

        sessions = fetch_all(db_path, "SELECT * FROM training_sessions")
        assert len(sessions) >= 1

        tasks = fetch_all(db_path, "SELECT * FROM generated_tasks")
        assert len(tasks) >= 1

    def test_script_is_idempotent(self):
        """连续运行两次仍通过。"""
        db_path = str(temp_db_path("demo_idempotent"))
        init_database(db_path)

        r1 = _run_seed(db_path)
        assert r1.returncode == 0

        r2 = _run_seed(db_path)
        assert r2.returncode == 0, f"第二次运行失败:\n{r2.stderr}"

    def test_no_real_api_key_in_output(self):
        db_path = str(temp_db_path("demo_nokey"))
        init_database(db_path)

        result = _run_seed(db_path)
        assert "sk-" not in result.stdout
        assert "sk-" not in result.stderr
