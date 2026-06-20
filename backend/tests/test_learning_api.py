"""文本分析 API 路由测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import init_database
from app.main import create_app
from app.config import Settings
from app.repositories.training import create_training_session
from app.repositories.users import create_user
from temp_paths import temp_db_path


@pytest.fixture
def client():
    db_path = str(temp_db_path("learning_api"))
    init_database(db_path)
    settings = Settings(
        app_name="LingoForge Test",
        database_path=db_path,
        cors_origins=[],
        llm_mode="mock",
        llm_provider="deepseek",
    )
    app = create_app(settings)
    return TestClient(app)


class TestAnalyzeTextAPI:
    """POST /api/learning/analyze-text 测试。"""

    def test_normal_analysis_success(self, client):
        response = client.post(
            "/api/learning/analyze-text",
            json={
                "raw_text": "Climate change is a pressing global challenge that affects ecosystems worldwide.",
                "target_abilities": ["VOCABULARY_CONTEXT"],
                "max_keywords": 5,
                "generate_exercise": True,
            },
            headers={"X-LingoForge-User-Id": "1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"].startswith("analysis_")
        assert data["source"] == "MOCK_DETERMINISTIC"
        assert len(data["raw_text"]) > 0
        assert isinstance(data["keywords"], list)

    def test_user_id_in_body_rejected(self, client):
        response = client.post(
            "/api/learning/analyze-text",
            json={
                "raw_text": "Hello world.",
                "user_id": 1,
            },
            headers={"X-LingoForge-User-Id": "1"},
        )
        assert response.status_code == 422

    def test_missing_user_header_rejected(self, client):
        response = client.post(
            "/api/learning/analyze-text",
            json={"raw_text": "Hello world."},
        )
        assert response.status_code == 422

    def test_invalid_user_header_rejected(self, client):
        response = client.post(
            "/api/learning/analyze-text",
            json={"raw_text": "Hello world."},
            headers={"X-LingoForge-User-Id": "not_a_number"},
        )
        assert response.status_code == 422

    def test_empty_raw_text_rejected(self, client):
        response = client.post(
            "/api/learning/analyze-text",
            json={"raw_text": ""},
            headers={"X-LingoForge-User-Id": "1"},
        )
        assert response.status_code == 422

    def test_optional_session_header_accepted(self, client):
        response = client.post(
            "/api/learning/analyze-text",
            json={"raw_text": "Hello world from the test environment."},
            headers={
                "X-LingoForge-User-Id": "1",
                "X-LingoForge-Session-Id": "42",
            },
        )
        assert response.status_code == 200

    def test_generate_exercise_false_works(self, client):
        response = client.post(
            "/api/learning/analyze-text",
            json={
                "raw_text": "Technology shapes the way people learn.",
                "generate_exercise": False,
            },
            headers={"X-LingoForge-User-Id": "1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exercise"] is None


class TestAnalyzeTextCreateTask:
    """POST /api/learning/analyze-text/create-task 测试。"""

    def test_正常分析并创建_task(self, client: TestClient) -> None:
        db_path = _get_db_path(client)
        uid = create_user(db_path, "分析任务测试用户")
        sid = create_training_session(db_path, uid, stage="FIRST_MAIN")
        resp = client.post(
            "/api/learning/analyze-text/create-task",
            json={
                "raw_text": "Climate change is a pressing challenge for ecosystems worldwide.",
                "target_abilities": ["VOCABULARY_CONTEXT"],
                "max_keywords": 3,
                "generate_exercise": True,
            },
            headers={
                "X-LingoForge-User-Id": str(uid),
                "X-LingoForge-Session-Id": str(sid),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis" in data
        assert data["task_id"] >= 1
        assert data["analysis"]["analysis_id"].startswith("analysis_")

    def test_请求体含身份字段返回_422(self, client: TestClient) -> None:
        db_path = _get_db_path(client)
        uid = create_user(db_path, "身份测试用户2")
        sid = create_training_session(db_path, uid, stage="FIRST_MAIN")
        resp = client.post(
            "/api/learning/analyze-text/create-task",
            json={
                "raw_text": "Hello world.",
                "user_id": uid,
            },
            headers={
                "X-LingoForge-User-Id": str(uid),
                "X-LingoForge-Session-Id": str(sid),
            },
        )
        assert resp.status_code == 422

    def test_使用其他用户_session_返回_403(self, client: TestClient) -> None:
        db_path = _get_db_path(client)
        uid1 = create_user(db_path, "用户A2")
        uid2 = create_user(db_path, "用户B2")
        sid = create_training_session(db_path, uid2, stage="FIRST_MAIN")
        resp = client.post(
            "/api/learning/analyze-text/create-task",
            json={
                "raw_text": "Climate change is a pressing challenge.",
                "target_abilities": ["VOCABULARY_CONTEXT"],
            },
            headers={
                "X-LingoForge-User-Id": str(uid1),
                "X-LingoForge-Session-Id": str(sid),
            },
        )
        assert resp.status_code == 403


def _get_db_path(client: TestClient) -> str:
    """从 TestClient 获取数据库路径。"""
    from app.api.training import get_settings as get_training_settings
    settings = client.app.dependency_overrides[get_training_settings]()
    return str(settings.database_path)
