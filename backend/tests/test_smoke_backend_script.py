"""后端 smoke 测试脚本测试。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_smoke() -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[2] / "scripts" / "smoke_backend.py"
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=60,
    )


class TestSmokeBackendScript:
    """后端 smoke 脚本测试。"""

    def test_smoke_script_exits_zero(self):
        result = _run_smoke()
        assert result.returncode == 0, (
            f"smoke 脚本退出码 {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    def test_smoke_output_contains_health(self):
        result = _run_smoke()
        assert "health" in result.stdout.lower()

    def test_smoke_output_contains_profile(self):
        result = _run_smoke()
        assert "profile" in result.stdout.lower()

    def test_smoke_output_contains_isolated(self):
        result = _run_smoke()
        assert "isolated" in result.stdout.lower()

    def test_smoke_output_contains_sidequest(self):
        result = _run_smoke()
        assert "sidequest" in result.stdout.lower() or "副线" in result.stdout

    def test_smoke_output_contains_learning(self):
        result = _run_smoke()
        assert "learning" in result.stdout.lower() or "create-task" in result.stdout.lower()

    def test_smoke_output_contains_training(self):
        result = _run_smoke()
        assert "training" in result.stdout.lower() or "训练" in result.stdout

    def test_smoke_output_contains_passing_marker(self):
        result = _run_smoke()
        assert "通过" in result.stdout or "全部通过" in result.stdout or "OK" in result.stdout

    def test_no_api_key_leaked(self):
        result = _run_smoke()
        assert "sk-" not in result.stdout
        assert "sk-" not in result.stderr
