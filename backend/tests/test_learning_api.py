"""文本分析 API 路由测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.config import Settings
from temp_paths import temp_db_path


@pytest.fixture
def client():
    db_path = str(temp_db_path("learning_api"))
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
