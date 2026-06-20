"""训练会话 API 测试。

测试 POST /api/training/sessions 和 GET /api/training/sessions 端点。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.repositories.training import create_training_session
from app.repositories.users import create_user
from temp_paths import temp_db_path


@pytest.fixture
def db_path() -> str:
    path = str(temp_db_path("training_session_api"))
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


class TestCreateTrainingSession:
    """测试 POST /api/training/sessions 端点。"""

    def test_正常创建_session(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "训练测试用户")
        resp = client.post(
            "/api/training/sessions",
            json={"stage": "FIRST_MAIN"},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] >= 1
        assert data["user_id"] == uid
        assert data["stage"] == "FIRST_MAIN"
        assert data["status"] == "IN_PROGRESS"

    def test_非法_stage_返回_422或400(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "stage验证用户")
        resp = client.post(
            "/api/training/sessions",
            json={"stage": "INVALID_STAGE"},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code in (400, 422)

    def test_缺少用户头返回_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/training/sessions",
            json={"stage": "FIRST_MAIN"},
        )
        assert resp.status_code == 422

    def test_请求体禁止身份字段(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "身份测试")
        resp = client.post(
            "/api/training/sessions",
            json={"stage": "FIRST_MAIN", "user_id": uid},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 422


class TestListTrainingSessions:
    """测试 GET /api/training/sessions 端点。"""

    def test_正常列出当前用户_session(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "列表测试用户")
        sid1 = create_training_session(db_path, uid, stage="FIRST_MAIN", status="IN_PROGRESS")
        sid2 = create_training_session(db_path, uid, stage="DIAGNOSTIC", status="IN_PROGRESS")
        resp = client.get(
            "/api/training/sessions",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert len(data["sessions"]) >= 2

    def test_其他用户_session_不出现在列表中(self, client: TestClient, db_path: str) -> None:
        uid1 = create_user(db_path, "用户A")
        uid2 = create_user(db_path, "用户B")
        create_training_session(db_path, uid2, stage="FIRST_MAIN")
        resp = client.get(
            "/api/training/sessions",
            headers={"X-LingoForge-User-Id": str(uid1)},
        )
        assert resp.status_code == 200
        data = resp.json()
        other_ids = {s["user_id"] for s in data["sessions"]}
        assert uid2 not in other_ids

    def test_按_id_降序排序(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "排序测试用户")
        sids = []
        for stage in ("DIAGNOSTIC", "FIRST_MAIN", "SIDEQUEST"):
            sids.append(create_training_session(db_path, uid, stage=stage))
        resp = client.get(
            "/api/training/sessions",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        ids = [s["id"] for s in data["sessions"]]
        assert ids == sorted(ids, reverse=True)

    def test_缺少用户头返回_422(self, client: TestClient) -> None:
        resp = client.get("/api/training/sessions")
        assert resp.status_code == 422
