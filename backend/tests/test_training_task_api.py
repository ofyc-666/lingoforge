"""训练任务列表与详情 API 测试。

测试 GET /api/training/sessions/{session_id}/tasks 和 GET /api/training/tasks/{task_id}。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.repositories.training import create_generated_task, create_training_session
from app.repositories.users import create_user
from factories import create_multiple_choice_task, create_user_with_session
from temp_paths import temp_db_path


@pytest.fixture
def db_path() -> str:
    path = str(temp_db_path("training_task_api"))
    init_database(path)
    return path


@pytest.fixture
def settings(db_path: str) -> Settings:
    return Settings(
        app_name="LingoForge Test",
        database_path=db_path,
        cors_origins=[],
        llm_mode="mock",
        llm_provider="deepseek",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    return TestClient(app)


class TestListSessionTasks:
    """GET /api/training/sessions/{session_id}/tasks 测试。"""

    def test_正常列出_session_下任务(self, client: TestClient, db_path: str) -> None:
        ctx = create_user_with_session(db_path)
        uid, sid = ctx["user_id"], ctx["session_id"]
        create_multiple_choice_task(db_path, user_id=uid, session_id=sid)
        resp = client.get(
            f"/api/training/sessions/{sid}/tasks",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 1

    def test_其他用户_session_下任务列表被拒绝(self, client: TestClient, db_path: str) -> None:
        ctx = create_user_with_session(db_path)
        _, sid = ctx["user_id"], ctx["session_id"]
        uid2 = create_user(db_path, "其他用户")
        resp = client.get(
            f"/api/training/sessions/{sid}/tasks",
            headers={"X-LingoForge-User-Id": str(uid2)},
        )
        assert resp.status_code == 403

    def test_不存在的_session_返回_404(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "测试用户")
        resp = client.get(
            "/api/training/sessions/99999/tasks",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 404


class TestGetTaskDetail:
    """GET /api/training/tasks/{task_id} 测试。"""

    def test_正常读取单个_task(self, client: TestClient, db_path: str) -> None:
        ctx = create_user_with_session(db_path)
        uid, sid = ctx["user_id"], ctx["session_id"]
        tid = create_multiple_choice_task(db_path, user_id=uid, session_id=sid)
        resp = client.get(
            f"/api/training/tasks/{tid}",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == tid
        assert data["session_id"] == sid
        assert data["target_ability"] == "VOCABULARY_CONTEXT"

    def test_其他用户_task_读取被拒绝(self, client: TestClient, db_path: str) -> None:
        ctx = create_user_with_session(db_path)
        uid1, sid = ctx["user_id"], ctx["session_id"]
        tid = create_multiple_choice_task(db_path, user_id=uid1, session_id=sid)
        uid2 = create_user(db_path, "其他用户")
        resp = client.get(
            f"/api/training/tasks/{tid}",
            headers={"X-LingoForge-User-Id": str(uid2)},
        )
        assert resp.status_code == 403

    def test_不存在的_task_返回_404(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "测试用户")
        resp = client.get(
            "/api/training/tasks/99999",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 404
