"""用户画像 API 测试。

测试 GET /api/profile/summary 和 POST /api/profile/goal 端点。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.repositories.users import (
    create_profile_snapshot,
    create_profile_suggestion,
    create_user,
    save_user_goal,
)
from temp_paths import temp_db_path


@pytest.fixture
def db_path() -> str:
    path = str(temp_db_path("profile_api"))
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


# --------------- GET /api/profile/summary ---------------


class TestProfileSummary:
    """测试 GET /api/profile/summary 端点。"""

    def test_正常用户返回摘要(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "测试张三")
        create_profile_snapshot(
            db_path, uid, source="DIAGNOSTIC",
            profile={"VOCABULARY_CONTEXT": {"level": "beginner"}},
        )
        resp = client.get(
            "/api/profile/summary",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert data["user"]["id"] == uid
        assert data["user"]["display_name"] == "测试张三"
        assert "latest_goal" in data
        assert "latest_profile" in data
        assert "pending_suggestions" in data

    def test_缺少用户头返回_422(self, client: TestClient) -> None:
        resp = client.get("/api/profile/summary")
        assert resp.status_code == 422

    def test_不存在用户返回_404(self, client: TestClient) -> None:
        resp = client.get(
            "/api/profile/summary",
            headers={"X-LingoForge-User-Id": "99999"},
        )
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["code"] == "USER_NOT_FOUND"

    def test_其他用户数据不出现在响应中(self, client: TestClient, db_path: str) -> None:
        uid1 = create_user(db_path, "用户甲")
        uid2 = create_user(db_path, "用户乙")
        save_user_goal(db_path, uid2, exam_type="CET-6", target_score=600)
        create_profile_snapshot(
            db_path, uid2, source="DIAGNOSTIC",
            profile={"VOCABULARY_CONTEXT": {"level": "advanced"}},
        )
        resp = client.get(
            "/api/profile/summary",
            headers={"X-LingoForge-User-Id": str(uid1)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["id"] == uid1
        assert data["user"]["display_name"] == "用户甲"

    def test_待审核建议出现在摘要中(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "测试丁")
        create_profile_suggestion(
            db_path, uid,
            ability="VOCABULARY_CONTEXT",
            direction="IMPROVE",
            reason="正确率高",
            evidence_refs=[1],
        )
        resp = client.get(
            "/api/profile/summary",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["pending_suggestions"]) >= 1
        suggestion = data["pending_suggestions"][0]
        assert suggestion["validation_status"] == "NEEDS_REVIEW"


# --------------- POST /api/profile/goal ---------------


class TestProfileGoal:
    """测试 POST /api/profile/goal 端点。"""

    def test_正常保存目标(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "目标测试用户")
        resp = client.post(
            "/api/profile/goal",
            json={
                "exam_type": "CET-6",
                "days_until_exam": 30,
                "target_score": 550,
                "daily_minutes": 30,
                "self_reported_weaknesses": ["vocabulary"],
                "interest_topics": ["technology"],
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["goal_id"] >= 1
        assert data["user_id"] == uid

    def test_请求体含_user_id_返回_422(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "身份测试用户")
        resp = client.post(
            "/api/profile/goal",
            json={
                "user_id": uid,
                "exam_type": "CET-6",
                "target_score": 500,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 422

    def test_负数时间返回_422(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "验证测试用户")
        resp = client.post(
            "/api/profile/goal",
            json={
                "exam_type": "CET-6",
                "days_until_exam": -1,
                "daily_minutes": 30,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 422

    def test_负数分数返回_422(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "分数验证用户")
        resp = client.post(
            "/api/profile/goal",
            json={
                "exam_type": "CET-6",
                "target_score": -100,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 422

    def test_不存在用户返回_404(self, client: TestClient) -> None:
        resp = client.post(
            "/api/profile/goal",
            json={
                "exam_type": "CET-6",
                "target_score": 550,
            },
            headers={"X-LingoForge-User-Id": "99999"},
        )
        assert resp.status_code == 404
