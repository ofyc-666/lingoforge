"""训练提交与结果查询 API 路由测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.repositories.training import get_generated_task
from app.repositories.users import create_user
from factories import create_multiple_choice_task, create_user_with_session
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = str(temp_db_path("training_api"))
    init_database(path)
    return path


@pytest.fixture
def settings(db_path):
    return Settings(
        app_name="LingoForge Test",
        database_path=db_path,
        cors_origins=[],
        llm_mode="mock",
        llm_provider="deepseek",
    )


@pytest.fixture
def client(settings):
    app = create_app(settings)
    return TestClient(app)


def _create_user_and_task(db_path: str) -> tuple[int, int, int, str]:
    """创建测试用户、session 和 MULTIPLE_CHOICE 任务。返回 (user_id, session_id, task_id, db_path)。"""
    ctx = create_user_with_session(db_path)
    uid, sid = ctx["user_id"], ctx["session_id"]
    tid = create_multiple_choice_task(db_path, user_id=uid, session_id=sid)
    return uid, sid, tid, db_path


class TestTestFactory:
    """测试工厂数据创建。"""

    def test_factory_created_task_is_readable(self, db_path):
        ctx = create_user_with_session(db_path)
        tid = create_multiple_choice_task(db_path, user_id=ctx["user_id"], session_id=ctx["session_id"])
        task = get_generated_task(db_path, tid)
        assert task is not None
        assert task["user_id"] == ctx["user_id"]
        assert task["task_type"] == "LOW_PRESSURE_LEARNING"
        content = task["content_json"]
        assert len(content["questions"]) == 2


class TestTrainingSubmitAPI:
    """POST /api/training/tasks/{task_id}/submit 测试。"""

    def test_normal_submit_success(self, client, db_path):
        uid, sid, tid, _ = _create_user_and_task(db_path)
        response = client.post(
            f"/api/training/tasks/{tid}/submit",
            json={
                "answers": [
                    {"question_id": "q1", "answer": "A"},
                    {"question_id": "q2", "answer": "B"},
                ],
                "time_spent_seconds": 30,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == tid
        assert data["session_id"] == sid
        assert data["score"]["total"] == 2
        assert data["evidence_id"] >= 1

    def test_identity_fields_in_body_rejected(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        response = client.post(
            f"/api/training/tasks/{tid}/submit",
            json={
                "answers": [{"question_id": "q1", "answer": "A"}],
                "user_id": uid,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 422

    def test_other_user_task_rejected(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        other_uid = create_user(db_path, "其他")
        response = client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(other_uid)},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "TASK_ACCESS_DENIED"

    def test_invalid_answers_rejected(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        response = client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": []},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 422

    def test_nonexistent_task_not_found(self, client, db_path):
        uid = create_user(db_path, "测试用户")
        response = client.post(
            "/api/training/tasks/99999/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "TASK_NOT_FOUND"

    def test_missing_user_header_rejected(self, client, db_path):
        response = client.post(
            "/api/training/tasks/1/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
        )
        assert response.status_code == 422


class TestTrainingResultAPI:
    """GET /api/training/tasks/{task_id}/result 测试。"""

    def test_no_submission_returns_null(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        response = client.get(
            f"/api/training/tasks/{tid}/result",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["task_id"] == tid
        assert data["latest_submission"] is None

    def test_with_submission(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        # 先提交
        client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        # 再查询
        response = client.get(
            f"/api/training/tasks/{tid}/result",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["latest_submission"] is not None
        assert data["latest_submission"]["evidence_id"] >= 1

    def test_two_submissions_returns_latest(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        # 两次提交
        client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": [{"question_id": "q1", "answer": "B"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        response = client.get(
            f"/api/training/tasks/{tid}/result",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        data = response.json()
        assert data["latest_submission"]["evidence_id"] >= 2

    def test_other_user_query_rejected(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        other_uid = create_user(db_path, "其他查询用户")
        response = client.get(
            f"/api/training/tasks/{tid}/result",
            headers={"X-LingoForge-User-Id": str(other_uid)},
        )
        assert response.status_code == 403
