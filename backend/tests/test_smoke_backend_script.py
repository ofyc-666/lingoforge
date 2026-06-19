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
    """后��� smoke 脚本测试。"""

    def test_smoke_script_exits_zero(self):
        result = _run_smoke()
        assert result.returncode == 0, (
            f"smoke 脚本退出码 {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    def test_smoke_script_output_mentions_health(self):
        result = _run_smoke()
        assert "health" in result.stdout.lower()
